from dotenv import load_dotenv
from flask import Flask, get_flashed_messages, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
from flask_sendgrid import SendGrid
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail as SendGridMail
from werkzeug.utils import secure_filename
from jinja2 import Template
from itsdangerous import URLSafeTimedSerializer
import numpy as np
import logging
import secrets
import re
import os
import random
import MySQLdb
import hashlib
import pandas as pd
from modules.auth import auth_bp
from modules.classifier import predict_with_confidence
from tensorflow.keras.models import load_model

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(8))
serializer = URLSafeTimedSerializer(app.secret_key)
base_dir = os.path.abspath(os.path.dirname(__file__))

app.register_blueprint(auth_bp, url_prefix='/auth')

app.config['UPLOAD_FOLDER_USERS'] = os.path.join(base_dir, 'static/assets/img/users')
app.config['UPLOAD_FOLDER_ADMINS'] = os.path.join(base_dir, 'static/assets/img/admins')

# Log untuk memastikan jalur konfigurasi benar
logging.debug(f"UPLOAD_FOLDER_USERS: {app.config['UPLOAD_FOLDER_USERS']}")
logging.debug(f"UPLOAD_FOLDER_ADMINS: {app.config['UPLOAD_FOLDER_ADMINS']}")

# Konfigurasi MySQL
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB')

# Konfigurasi SendGrid
app.config['SENDGRID_API_KEY'] = os.getenv('SENDGRID_API_KEY')
app.config['SENDGRID_DEFAULT_FROM'] = os.getenv('SENDGRID_DEFAULT_FROM')
app.config['MAIL_SERVER'] = 'smtp.sendgrid.net'

app.config['UPLOAD_FOLDER_DETECTIONS'] = os.path.join(base_dir, 'static/assets/img/detections')

if not os.path.exists(app.config['UPLOAD_FOLDER_DETECTIONS']):
    os.makedirs(app.config['UPLOAD_FOLDER_DETECTIONS'])

mysql = MySQL(app)
sg = SendGridAPIClient(app.config['SENDGRID_API_KEY'])
# Fungsi untuk membuat koneksi ke database
def get_db():
    db = MySQLdb.connect(host=app.config['MYSQL_HOST'], user=app.config['MYSQL_USER'],
                         password=app.config['MYSQL_PASSWORD'], db=app.config['MYSQL_DB'], cursorclass=MySQLdb.cursors.DictCursor)
    return db, db.cursor()

def get_confidence_ran():
    return random.uniform(70, 88)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg'}

# Fungsi untuk mengenkripsi password
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def adjust_confidence(confidence):
    min_confidence = 70
    max_confidence = 85
    return np.clip(confidence, min_confidence, max_confidence)

# # Fungsi untuk melakukan prediksi dan mendapatkan confidence (untuk CNN model)
# def predict_with_confidence(model, input_data):
#     prediction = model.predict(input_data)
#     confidence = np.max(prediction) * 100  
#     adjusted_confidence = np.clip(confidence, 70, 88)
#     return prediction, adjusted_confidence

# Fungsi untuk mengirim kode verifikasi ke email
def send_verification_code(email, verification_code):
    template_path = os.path.join(base_dir, 'templates', 'verification_email.html')

    with open(template_path, 'r') as file:
        html_template = file.read()

    template = Template(html_template)

    html_content = template.render(verification_code=verification_code)

    message = SendGridMail(
        from_email='matimatech@gmail.com',
        to_emails=email,
        subject='Kode Verifikasi Anda',
        html_content=html_content
    )

    try:
        sg = SendGridAPIClient(app.config['SENDGRID_API_KEY'])
        response = sg.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
    except Exception as e:
        print(e)

def convert_to_float(value):
    try:
        return float(value.replace(',', '.'))
    except ValueError:
        return float(value)

@app.route('/')
def home():
    if 'logged_in' in session:
        return redirect(url_for('dashboard'))
    session['error'] = ''
    return render_template('home.html')

@app.route("/terms-condition")
def terms_condition():
    if 'logged_in' in session:
        return redirect(url_for('terms_condition_user'))
    return render_template("terms-condition.html")

@app.route("/terms-condition-user")
def terms_condition_user():
    if 'logged_in' not in session:
        return redirect(url_for('terms_condition'))
    return render_template("terms-condition-user.html")

@app.route('/dashboard', methods=['GET'])
def dashboard():
    if 'logged_in' not in session:
        logging.debug("User not logged in, redirecting to login page.")
        return redirect(url_for('auth.login'))

    user_type = session.get('user_type')
    if user_type not in ['admin', 'pengunjung']:
        flash('Anda tidak memiliki hak akses.', 'error')
        return redirect(url_for('auth.login'))

    db, cur = get_db()

    # Ambil jumlah total pasien
    cur.execute("SELECT COUNT(*) AS total_patients FROM patients")
    total_patients = cur.fetchone()['total_patients']

    # Ambil jumlah pasien dengan hasil pemeriksaan yang mengandung "Kanker Payudara"
    cur.execute("SELECT COUNT(*) AS total_tumor_otak FROM patients WHERE hasil_pemeriksaan LIKE '%Tumor Otak%'")
    total_tumor_otak = cur.fetchone()['total_tumor_otak']

    # Ambil jumlah pasien dengan hasil pemeriksaan yang mengandung "Kanker Payudara"
    cur.execute("SELECT COUNT(*) AS total_non_tumor_otak FROM patients WHERE hasil_pemeriksaan LIKE '%Non-Tumor Otak%'")
    total_non_tumor_otak = cur.fetchone()['total_non_tumor_otak']

    # Ambil data pasien untuk ditampilkan dalam tabel
    cur.execute("SELECT * FROM patients")
    patients = cur.fetchall()

    db.close()

    # Untuk admin
    if user_type == 'admin':
        admin_email = session.get('user_email')

        db, cur = get_db()
        cur.execute("SELECT * FROM admins WHERE email = %s", (admin_email,))
        admin_data = cur.fetchone()
        db.close()

        admin_name = session.get('user_name')
        admin_profile_picture = admin_data.get('profile_picture')

        if admin_profile_picture:
            admin_profile_picture = url_for('static', filename=f'assets/img/admins/{admin_profile_picture}')

        return render_template('dashboard.html', user_type=user_type, total_patients=total_patients,
                               total_tumor_otak=total_tumor_otak, total_non_tumor_otak=total_non_tumor_otak,
                               admin_name=admin_name, admin_profile_picture=admin_profile_picture,
                               admin_email=admin_email, patients=patients)

    # Untuk pengunjung
    elif user_type == 'pengunjung':
        user_email = session.get('user_email')

        db, cur = get_db()
        cur.execute("SELECT * FROM users WHERE email = %s", (user_email,))
        user_data = cur.fetchone()
        db.close()

        user_name = session.get('user_name')
        user_profile_picture = user_data.get('profile_picture')

        if user_profile_picture:
            user_profile_picture = url_for('static', filename=f'assets/img/users/{user_profile_picture}')

        return render_template('dashboard.html', user_type=user_type, total_patients=total_patients,
                               total_tumor_otak=total_tumor_otak, total_non_tumor_otak=total_non_tumor_otak,
                               user_name=user_name, user_profile_picture=user_profile_picture,
                               user_email=user_email, patients=patients)

@app.route('/classify', methods=['GET', 'POST'])
def classify():
    if 'logged_in' not in session:
        return redirect(url_for('auth.login'))

    user_type = session.get('user_type')
    user_name = session.get('user_name')
    user_email = session.get('user_email')
    user_profile_picture = session.get('user_profile_picture')

    if request.method == 'POST':
        if 'image' not in request.files:
            flash('Tidak ada file gambar yang diunggah!', 'error')
            return redirect(request.url)

        file = request.files['image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            user_filename = f"{user_email}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER_DETECTIONS'], user_filename)

            if not os.path.exists(app.config['UPLOAD_FOLDER_DETECTIONS']):
                os.makedirs(app.config['UPLOAD_FOLDER_DETECTIONS'])

            file.save(file_path)

            # Panggil fungsi prediksi dengan gambar yang diunggah
            result, confidence, img_base64, output_img_path = predict_with_confidence(file_path, user_email)
            
            # Simpan hasil deteksi dan confidence di database
            hasil_pemeriksaan = f"Hasil deteksi: {result}"

            confidence_rounded = round(confidence, 4)

            db, cur = get_db()
            try:
                cur.execute("""
                    INSERT INTO patients (nama, hasil_pemeriksaan, confidence_score)
                    VALUES (%s, %s, %s)
                """, (request.form['nama'], hasil_pemeriksaan, confidence_rounded))
                db.commit()
            except Exception as e:
                logging.error(f"Error during database insertion: {e}")
                db.rollback()
            finally:
                db.close()

            return render_template('classify.html', result=result, confidence=confidence_rounded,
                                   img_base64=img_base64, user_type=user_type, name=user_name,
                                   email=user_email, profile_picture=user_profile_picture, 
                                   output_img_path=output_img_path)

    return render_template('classify.html', user_type=user_type, name=user_name, email=user_email, profile_picture=user_profile_picture)

@app.route('/user-profile-settings', methods=['GET', 'POST'])
def user_profile_settings():
    if 'logged_in' not in session:
        return redirect(url_for('auth.login'))

    # Ambil data user dari session
    user_email = session.get('user_email')
    user_name = session.get('user_name')
    user_profile_picture = session.get('user_profile_picture')

    if request.method == 'POST':
        # Proses pengubahan data profil user
        new_name = request.form.get('name')
        new_profile_picture = request.files.get('photo')

        # Proses upload foto
        if new_profile_picture:
            filename = secure_filename(new_profile_picture.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER_USERS'], filename)
            new_profile_picture.save(filepath)

            # Update nama file foto profil di database
            db, cur = get_db()
            try:
                cur.execute("""
                    UPDATE users
                    SET name = %s, profile_picture = %s
                    WHERE email = %s
                """, (new_name, filename, user_email))
                db.commit()
                flash("Profil berhasil diperbarui", "success")
                session['user_profile_picture'] = filename  
            except Exception as e:
                db.rollback()
                flash(f"Terjadi kesalahan: {e}", "error")
            finally:
                db.close()
        else:
            # Jika tidak ada foto baru, hanya update nama
            db, cur = get_db()
            try:
                cur.execute("""
                    UPDATE users
                    SET name = %s
                    WHERE email = %s
                """, (new_name, user_email))
                db.commit()
                flash("Profil berhasil diperbarui", "success")
            except Exception as e:
                db.rollback()
                flash(f"Terjadi kesalahan: {e}", "error")
            finally:
                db.close()

        return redirect(url_for('user_profile_settings'))

    return render_template('user-profile-settings.html', user_name=user_name, user_email=user_email, user_profile_picture=user_profile_picture)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
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
# Route ini menangani halaman dashboard yang hanya bisa diakses jika user sudah login.

def dashboard():
    if 'logged_in' not in session:
        logging.debug("User not logged in, redirecting to login page.")
        # Cek jika pengguna belum login, diarahkan ke halaman login.
        return redirect(url_for('auth.login'))

    user_type = session.get('user_type')
    user_id = session.get('user_id')
    # Mengambil data tipe pengguna dan ID user dari sesi yang sudah tersimpan.

    if user_type not in ['admin', 'pengunjung']:
        flash('Anda tidak memiliki hak akses.', 'error')
        # Jika tipe user bukan admin atau pengunjung, beri flash message dan arahkan ke login.
        return redirect(url_for('auth.login'))

    db, cur = get_db()
    # Membuka koneksi ke database dan mendapatkan cursor untuk eksekusi query.

    # Query untuk mendapatkan statistik pasien berdasarkan ID user
    cur.execute("""
        SELECT 
            COUNT(*) AS total_patients,
            SUM(CASE WHEN hasil_pemeriksaan LIKE '%%Hasil deteksi: Kanker%%' THEN 1 ELSE 0 END) AS total_kanker_payudara,
            SUM(CASE WHEN hasil_pemeriksaan LIKE '%%Non-Kanker%%' THEN 1 ELSE 0 END) AS total_non_kanker_payudara
        FROM patients 
        WHERE user_id = %s
    """, (user_id,))
    stats = cur.fetchone()
    # Mengambil data statistik seperti total pasien, jumlah yang terdeteksi kanker payudara, dan non-kanker.

    total_patients = stats['total_patients']
    total_kanker_payudara = stats['total_kanker_payudara']
    total_non_kanker_payudara = stats['total_non_kanker_payudara']
    # Menyimpan hasil query ke variabel untuk digunakan di halaman dashboard.

    # Query untuk mengambil data pasien berdasarkan user ID
    cur.execute("SELECT * FROM patients WHERE user_id = %s", (user_id,))
    patients = cur.fetchall()
    # Mengambil semua data pasien yang terdaftar oleh user ini.

    # Query untuk mengambil nama dan gambar profil user dari tabel users
    cur.execute("SELECT profile_picture, name FROM users WHERE id = %s", (user_id,))
    user_data = cur.fetchone()
    # Menarik data nama dan gambar profil pengguna.

    user_name = user_data.get('name', 'User')
    user_profile_picture = user_data.get('profile_picture', None)
    # Mengambil nama user dan gambar profilnya (jika ada). Jika tidak ada, akan menggunakan 'User' sebagai fallback.

    # Tentukan URL gambar profil berdasarkan tipe user (admin/pengunjung)
    if user_profile_picture:
        if user_type == 'admin':
            user_profile_picture = url_for('static', filename=f'assets/img/admins/{user_profile_picture}')
        else:
            user_profile_picture = url_for('static', filename=f'assets/img/users/{user_profile_picture}')
    else:
        user_profile_picture = url_for('static', filename='assets/img/default-profile.jpg')
    # Jika ada gambar profil, tentukan URL-nya berdasarkan folder yang sesuai (admin atau pengunjung). Kalau gak ada, pakai gambar default.

    db.close()
    # Tutup koneksi database setelah selesai.

    # Render halaman dashboard sesuai dengan tipe user (admin atau pengunjung)
    if user_type == 'admin':
        admin_email = session.get('user_email')
        # Ambil email admin dari sesi.
        return render_template('dashboard.html', user_type=user_type, total_patients=total_patients,
                               total_kanker_payudara=total_kanker_payudara, total_non_kanker_payudara=total_non_kanker_payudara,
                               user_name=user_name, user_profile_picture=user_profile_picture,
                               admin_email=admin_email, patients=patients)
        # Jika user admin, tampilkan dashboard dengan informasi statistik dan data pasien.

    elif user_type == 'pengunjung':
        user_email = session.get('user_email')
        # Ambil email pengguna pengunjung dari sesi.
        return render_template('dashboard.html', user_type=user_type, total_patients=total_patients,
                               total_kanker_payudara=total_kanker_payudara, total_non_kanker_payudara=total_non_kanker_payudara,
                               user_name=user_name, user_profile_picture=user_profile_picture,
                               user_email=user_email, patients=patients)
        # Jika user pengunjung, tampilkan dashboard yang serupa tapi dengan informasi pengguna pengunjung.



@app.route('/classify', methods=['GET', 'POST'])
# Route untuk halaman classify yang bisa menerima request GET dan POST.
def classify():
    if 'logged_in' not in session:
        return redirect(url_for('auth.login'))
        # Cek apakah pengguna sudah login atau belum. Kalau belum, diarahkan ke halaman login.

    user_type = session.get('user_type')
    user_id = session.get('user_id')
    user_name = session.get('user_name')
    user_email = session.get('user_email')
    user_profile_picture = session.get('user_profile_picture')
    # Ambil data pengguna (tipe, id, nama, email, gambar profil) yang sudah disimpan di sesi.

    if request.method == 'POST':
        if 'image' not in request.files:
            flash('Tidak ada file gambar yang diunggah!', 'error')
            return redirect(request.url)
            # Cek apakah ada gambar yang diupload, kalau gak ada, kasih pesan error dan kembali ke halaman yang sama.

        file = request.files['image']
        if file and allowed_file(file.filename):
            # Cek apakah file yang diupload punya ekstensi yang diperbolehkan (PNG, JPG, JPEG).
            filename = secure_filename(file.filename)
            user_filename = f"{user_email}_{filename}"
            # Pastikan nama file aman, dan buat nama file baru dengan menggabungkan email user supaya unik.

            file_path = os.path.join(app.config['UPLOAD_FOLDER_DETECTIONS'], user_filename)
            # Tentukan lokasi penyimpanan file di server.

            if not os.path.exists(app.config['UPLOAD_FOLDER_DETECTIONS']):
                os.makedirs(app.config['UPLOAD_FOLDER_DETECTIONS'])
                # Kalau folder penyimpanan file belum ada, buat dulu foldernya.

            file.save(file_path)
            # Simpan file yang diupload ke path yang sudah ditentukan.

            # Panggil fungsi prediksi dengan gambar yang diupload
            result, confidence, img_base64, output_img_path = predict_with_confidence(file_path, user_email)
            # Setelah gambar diupload, panggil fungsi prediksi untuk mendapatkan hasil deteksi dan confidence.

            # Simpan hasil deteksi dan confidence di database
            hasil_pemeriksaan = f"Hasil deteksi: {result}"
            confidence_rounded = round(confidence, 3)
            db, cur = get_db()
            # Ambil koneksi ke database dan buat cursor untuk eksekusi query.

            try:
                cur.execute("""
                    INSERT INTO patients (
                        nama, 
                        hasil_pemeriksaan, 
                        confidence_score, 
                        user_id,
                        created_at
                    ) VALUES (%s, %s, %s, %s, NOW())
                """, (
                    request.form['nama'], 
                    hasil_pemeriksaan, 
                    confidence_rounded, 
                    user_id
                ))
                db.commit()
                # Simpan data hasil pemeriksaan ke dalam tabel patients di database.
            except Exception as e:
                logging.error(f"Error during database insertion: {e}")
                db.rollback()
                # Kalau ada error saat menyimpan ke database, log error-nya dan batalkan perubahan.

            finally:
                db.close()
                # Tutup koneksi database setelah operasi selesai.

            # Render halaman classify dengan hasil prediksi, confidence, gambar dalam format base64, dan gambar output.
            return render_template('classify.html', result=result, confidence=confidence_rounded,
                                img_base64=img_base64, user_type=user_type, name=user_name,
                                email=user_email, profile_picture=user_profile_picture, 
                                output_img_path=output_img_path)

    # Kalau request-nya GET, cuma render halaman classify tanpa data tambahan.
    return render_template('classify.html', user_type=user_type, name=user_name, email=user_email, profile_picture=user_profile_picture)


@app.route('/user-profile-settings', methods=['GET', 'POST'])
# Route untuk halaman pengaturan profil user, menerima request GET dan POST.
def user_profile_settings():
    if 'logged_in' not in session:
        return redirect(url_for('auth.login'))
        # Cek apakah user sudah login atau belum. Kalau belum, langsung arahkan ke halaman login.

    # Ambil data user yang sudah disimpan di session (email, nama, foto profil).
    user_email = session.get('user_email')
    user_name = session.get('user_name')
    user_profile_picture = session.get('user_profile_picture')

    if request.method == 'POST':
        # Kalau request POST (ketika user submit form untuk ubah data profil):
        new_name = request.form.get('name')
        new_profile_picture = request.files.get('photo')
        # Ambil nama baru dan foto baru (kalau ada).

        if new_profile_picture:
            # Kalau ada foto baru yang di-upload:
            filename = secure_filename(new_profile_picture.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER_USERS'], filename)
            new_profile_picture.save(filepath)
            # Simpan foto baru dengan nama yang aman dan tempatkan di folder yang sudah diset.

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
                session['user_profile_picture'] = filename  # Update foto profil di session
            except Exception as e:
                db.rollback()
                flash(f"Terjadi kesalahan: {e}", "error")
            finally:
                db.close()
        else:
            # Kalau tidak ada foto baru, cuma update nama saja
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
        # Setelah proses update selesai, reload halaman supaya perubahan bisa terlihat.

    # Kalau request-nya GET (ketika pertama kali masuk ke halaman pengaturan profil):
    return render_template('user-profile-settings.html', user_name=user_name, user_email=user_email, user_profile_picture=user_profile_picture)
    # Render halaman pengaturan profil dengan data user yang sudah ada.



@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
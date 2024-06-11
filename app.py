from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
from flask_sendgrid import SendGrid
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail as SendGridMail
from werkzeug.utils import secure_filename
from jinja2 import Template
import logging
import secrets
import re
import os
import random
import MySQLdb
import hashlib
import pandas as pd
import pickle

app = Flask(__name__)
app.secret_key = secrets.token_hex(8)
app.config['UPLOAD_FOLDER_USERS'] = 'static/assets/img/users'
app.config['UPLOAD_FOLDER_ADMINS'] = 'static/assets/img/admins'


# Konfigurasi MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'db_puskesmas'

# Konfigurasi SendGrid
app.config['SENDGRID_API_KEY'] = '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'
app.config['SENDGRID_DEFAULT_FROM'] = 'matimatech@gmail.com'
app.config['MAIL_SERVER'] = 'smtp.sendgrid.net'
app.config['MAIL_USERNAME'] = 'apikey'

mysql = MySQL(app)
sg = SendGrid(app)

# Muat model dan transformer RFE
with open('./models/rf_model_rfe.pkl', 'rb') as model_file:
    rf_model_rfe = pickle.load(model_file)

with open('./models/rfe_rf_transformer.pkl', 'rb') as transformer_file:
    rfe_rf_transformer = pickle.load(transformer_file)
    
def load_model_and_transformer():
    global svm_model_rfe, rfe_transformer
    try:
        with open('./models/svm_model_rfe.pkl', 'rb') as f:
            svm_model_rfe = pickle.load(f)
        with open('./models/rfe_transformer.pkl', 'rb') as f:
            rfe_transformer = pickle.load(f)
    except Exception as e:
        logging.error(f"Error loading model or transformer: {e}")

load_model_and_transformer()

# Fungsi untuk membuat koneksi ke database
def get_db():
    db = MySQLdb.connect(host=app.config['MYSQL_HOST'], user=app.config['MYSQL_USER'],
                         password=app.config['MYSQL_PASSWORD'], db=app.config['MYSQL_DB'], cursorclass=MySQLdb.cursors.DictCursor)
    return db, db.cursor()

# Fungsi untuk mengenkripsi password
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def is_strong_password(password):
    if len(password) < 8:
        return False
    if not any(char.isupper() for char in password):
        return False
    if not any(char.islower() for char in password):
        return False
    if not any(char.isdigit() for char in password):
        return False
    if not any(char in '!@#$%^&*(),.?":{}|<>' for char in password):
        return False
    return True

# Fungsi untuk mengirim kode verifikasi ke email
def send_verification_code(email, verification_code):
    with open('templates/verification_email.html', 'r') as file:
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

@app.route('/index')
def index():
    if 'logged_in' in session:
        return redirect(url_for('logout'))
    
    session['error'] = ''
    
    name = session.get('name')
    profile = session.get('profile_picture')
    
    return render_template('index.html', name=name, profile=profile)

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

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'logged_in' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        logging.debug(f"Login attempt for email: {email}")

        db, cur = get_db()
        
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        db.close()
        
        if user:
            if hashlib.sha256(password.encode()).hexdigest() == user['password']:
                session['logged_in'] = True
                session['user_type'] = user['role']
                session['user_email'] = email
                session['user_name'] = user['name']
                session['user_qualification'] = user.get('qualification')
                session['user_profile_picture'] = user.get('profile_picture')
                logging.debug(f"User {email} logged in successfully.")
                return redirect(url_for('dashboard'))
            else:
                logging.debug("Incorrect password")
                flash('Password salah, silakan coba lagi.', 'error')
        else:
            logging.debug("Email not registered")
            flash('Email tidak terdaftar, silakan hubungi Admin', 'error')

    return render_template('login.html')

@app.route('/dashboard', methods=['GET'])
def dashboard():
    if 'logged_in' not in session:
        logging.debug("User not logged in, redirecting to login page.")
        return redirect(url_for('login'))

    user_type = session.get('user_type')
    if user_type not in ['admin', 'pengunjung']:
        flash('Anda tidak memiliki hak akses.', 'error')
        return redirect(url_for('login'))

    db, cur = get_db()
    cur.execute("SELECT * FROM patients")
    patients = cur.fetchall()
    db.close()

    patients_df = pd.DataFrame(patients, columns=['id', 'nama', 'haematocrit', 'haemoglobins', 'erythrocyte', 'leucocyte', 'thrombocyte', 'mch', 'mchc', 'mcv', 'umur', 'jenis_kelamin', 'hasil_klasifikasi'])
    
    # Mapping jenis_kelamin
    patients_df['jenis_kelamin'] = patients_df['jenis_kelamin'].map({0: 'Laki-laki', 1: 'Perempuan'})

    total_patients = len(patients_df)
    total_rujukan = len(patients_df[patients_df['hasil_klasifikasi'] == 'Rujukan Rumah Sakit'])
    total_rawat_jalan = len(patients_df[patients_df['hasil_klasifikasi'] == 'Rawat Jalan'])

    if user_type == 'admin':
        admin_email = session.get('user_email')

        db, cur = get_db()
        cur.execute("SELECT * FROM admins WHERE email = %s", (admin_email,))
        admin_data = cur.fetchone()
        db.close()

        admin_name = session.get('user_name')
        admin_kualifikasi = admin_data.get('qualification')
        admin_profil_pekerjaan = admin_data.get('job')
        admin_profile_picture = admin_data.get('profile_picture')

        if admin_profile_picture:
            admin_profile_picture = url_for('static', filename=f'assets/img/admins/{admin_profile_picture}')

        return render_template('dashboard.html', user_type=user_type, total_patients=total_patients, 
                               total_rujukan=total_rujukan, total_rawat_jalan=total_rawat_jalan,
                               admin_name=admin_name, admin_profile_picture=admin_profile_picture, 
                               admin_email=admin_email, admin_kualifikasi=admin_kualifikasi, 
                               admin_profil_pekerjaan=admin_profil_pekerjaan, patients=patients_df.to_dict(orient='records'))
    elif user_type == 'pengunjung':
        user_email = session.get('user_email')

        db, cur = get_db()
        cur.execute("SELECT * FROM users WHERE email = %s", (user_email,))
        user_data = cur.fetchone()
        db.close()

        user_name = session.get('user_name')
        user_qualification = user_data.get('qualification')
        user_profile_picture = user_data.get('profile_picture')

        if user_profile_picture:
            user_profile_picture = url_for('static', filename=f'assets/img/users/{user_profile_picture}')

        return render_template('dashboard.html', user_type=user_type, total_patients=total_patients, 
                               total_rujukan=total_rujukan, total_rawat_jalan=total_rawat_jalan,
                               user_name=user_name, user_profile_picture=user_profile_picture, 
                               user_email=user_email, user_qualification=user_qualification, patients=patients_df.to_dict(orient='records'))


@app.route('/admin-register', methods=['GET', 'POST'])
def admin_register():
    if 'logged_in' not in session or session.get('user_type') != 'admin':
        flash('Hanya admin yang dapat mengakses halaman ini.', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        qualification = request.form['qualification']

        if not name or not email or not password:
            flash('Semua field harus diisi.', 'error')
            return redirect(url_for('admin_register'))

        if not is_strong_password(password):
            flash('Password harus memiliki minimal 8 karakter, termasuk huruf besar, huruf kecil, angka, dan simbol.', 'error')
            return redirect(url_for('admin_register'))

        hashed_password = hash_password(password)

        db, cur = get_db()
        try:
            cur.execute("INSERT INTO users (name, email, password, qualification, role) VALUES (%s, %s, %s, %s, 'admin')", 
                        (name, email, hashed_password, qualification))
            db.commit()
            flash('Admin berhasil didaftarkan.', 'success')
        except MySQLdb.Error as e:
            db.rollback()
            flash(f'Terjadi kesalahan: {e}', 'error')
        finally:
            db.close()

        return redirect(url_for('dashboard'))

    return render_template('admin-register.html')

@app.route('/user-register', methods=['GET', 'POST'])
def user_register():
    if request.method == 'GET':
        flash_message = session.pop('user_register_success', None)
        return render_template('user-register.html', flash_message=flash_message)

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        qualification = request.form['qualification']

        if not name or not email or not password:
            flash('Semua field harus diisi.', 'error')
            return redirect(url_for('user_register'))

        if not is_strong_password(password):
            flash('Password harus memiliki minimal 8 karakter, termasuk huruf besar, huruf kecil, angka, dan simbol.', 'error')
            return redirect(url_for('user_register'))

        hashed_password = hash_password(password)
        
        verification_code = ''.join(random.choices('0123456789', k=6))
        
        session['fullname'] = name
        session['email'] = email
        session['password'] = hashed_password
        session['qualification'] = qualification
        session['verification_code'] = verification_code
        
        send_verification_code(email, verification_code)
        
        flash('Kode verifikasi telah dikirim ke email Anda. Silakan cek email Anda.', 'success')
        return redirect(url_for('verify'))

    return render_template('user-register.html')

@app.route('/verify', methods=['GET', 'POST'])
def verify():
    if request.method == 'POST':
        code1 = request.form.get('code1')
        code2 = request.form.get('code2')
        code3 = request.form.get('code3')
        code4 = request.form.get('code4')
        code5 = request.form.get('code5')
        code6 = request.form.get('code6')
        
        entered_code = f"{code1}{code2}{code3}{code4}{code5}{code6}"
        verification_code = session.get('verification_code', None)

        if verification_code and entered_code == verification_code:
            fullname = session.get('fullname')
            email = session.get('email')
            password = session.get('password')
            qualification = session.get('qualification')

            db, cur = get_db()
            try:
                cur.execute("INSERT INTO users (name, email, password, qualification, role) VALUES (%s, %s, %s, %s, 'pengunjung')", 
                            (fullname, email, password, qualification))
                db.commit()
                db.close()

                session.pop('verification_code')
                session.pop('fullname')
                session.pop('email')
                session.pop('password')
                session.pop('qualification')

                flash('Akun berhasil dibuat! Silakan login.', 'success')
                return redirect(url_for('login'))
            except MySQLdb.Error as e:
                db.rollback()
                flash(f'Terjadi kesalahan: {e}', 'error')
        else:
            flash('Kode verifikasi tidak valid! Silakan coba lagi.', 'error')
            return redirect(url_for('verify'))

    return render_template('verify.html')

@app.route('/admin-profile-settings', methods=['GET', 'POST'])
def admin_profile_settings():
    user_email = session.get('user_email')

    if not user_email:
        flash('Email tidak tersedia di session', 'error')
        return redirect(url_for('login'))

    if request.method == 'GET':
        user_name = session.get('user_name')
        user_qualification = session.get('user_qualification')
        user_profile_picture = session.get('user_profile_picture')
        result = request.args.get('result')
        return render_template('admin-profile-settings.html', admin_name=user_name, admin_email=user_email, admin_kualifikasi=user_qualification, admin_profile_picture=user_profile_picture, result=result)

    elif request.method == 'POST':
        name = request.form['name']
        kualifikasi = request.form['qualification']
        profile_picture = None

        if 'photo' in request.files:
            photo = request.files['photo']
            if photo.filename != '':
                filename = secure_filename(user_email + os.path.splitext(photo.filename)[1])
                photo.save(os.path.join(app.config['UPLOAD_FOLDER_ADMINS'], filename))
                profile_picture = filename
        try:
            db, cur = get_db()
            update_query = "UPDATE users SET name = %s, qualification = %s WHERE email = %s"
            cur.execute(update_query, (name, kualifikasi, user_email))
            db.commit()

            if profile_picture:
                cur.execute("UPDATE users SET profile_picture = %s WHERE email = %s", (profile_picture, user_email))
                db.commit()
                session['user_profile_picture'] = profile_picture

        except Exception as e:
            db.rollback()
            flash(f'Gagal memperbarui database: {e}', 'error')
        finally:
            db.close()

        session['user_name'] = name
        session['user_qualification'] = kualifikasi

        return redirect(url_for('admin_profile_settings'))





@app.route('/user-profile-settings', methods=['GET', 'POST'])
def user_profile_settings():
    user_email = session.get('user_email')

    if not user_email:
        flash('Email tidak tersedia di session', 'error')
        return redirect(url_for('login'))

    if request.method == 'GET':
        user_name = session.get('user_name')
        user_profile_picture = session.get('user_profile_picture')
        user_qualification = session.get('user_qualification')
        result = request.args.get('result')
        return render_template('user-profile-settings.html', user_name=user_name, user_email=user_email, user_profile_picture=user_profile_picture, user_qualification=user_qualification, result=result)

    elif request.method == 'POST':
        name = request.form['name']
        qualification = request.form['qualification']
        profile_picture = None

        if 'photo' in request.files:
            photo = request.files['photo']
            if photo.filename != '':
                filename = secure_filename(user_email + os.path.splitext(photo.filename)[1])
                photo.save(os.path.join(app.config['UPLOAD_FOLDER_USERS'], filename))
                profile_picture = filename

        try:
            db, cur = get_db()
            update_query = "UPDATE users SET name = %s, qualification = %s WHERE email = %s"
            cur.execute(update_query, (name, qualification, user_email))
            db.commit()

            if profile_picture:
                cur.execute("UPDATE users SET profile_picture = %s WHERE email = %s", (profile_picture, user_email))
                db.commit()
                session['user_profile_picture'] = profile_picture

        except Exception as e:
            db.rollback()
            flash(f'Gagal memperbarui database: {e}', 'error')
        finally:
            db.close()

        session['user_name'] = name
        session['user_qualification'] = qualification

        return redirect(url_for('user_profile_settings'))


@app.route('/classify', methods=['GET', 'POST'])
def classify():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    user_type = session.get('user_type')
    user_name = session.get('user_name')
    user_email = session.get('user_email')
    user_profile_picture = session.get('user_profile_picture')

    if request.method == 'GET':
        return render_template('classify.html', user_type=user_type, name=user_name, email=user_email, profile_picture=user_profile_picture)

    elif request.method == 'POST':
        data = request.form
        input_data = [[convert_to_float(data['haematocrit']), convert_to_float(data['haemoglobins']), convert_to_float(data['erythrocyte']),
                       convert_to_float(data['leucocyte']), convert_to_float(data['thrombocyte']), convert_to_float(data['mch']), 
                       convert_to_float(data['mchc']), convert_to_float(data['mcv']), int(data['umur']), int(data['jenis_kelamin'])]]

        logging.debug(f"Data Input for Prediction: {input_data}")
        
        try:
            transformed_data = rfe_transformer.transform(input_data)
            logging.debug(f"Transformed Data: {transformed_data}")
        except Exception as e:
            logging.error(f"Error during data transformation: {e}")
            flash('Terjadi kesalahan saat memproses data.', 'error')
            return redirect(url_for('classify'))

        try:
            prediction = svm_model_rfe.predict(transformed_data)[0]
            logging.debug(f"Prediction Result: {prediction}")
        except Exception as e:
            logging.error(f"Error during model prediction: {e}")
            flash('Terjadi kesalahan saat memproses prediksi.', 'error')
            return redirect(url_for('classify'))

        result = "Rujukan Rumah Sakit" if prediction == 1 else "Rawat Jalan"

        db, cur = get_db()
        try:
            cur.execute("INSERT INTO patients (nama, haematocrit, haemoglobins, erythrocyte, leucocyte, thrombocyte, mch, mchc, mcv, umur, jenis_kelamin, hasil_klasifikasi) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", 
                        (data['nama'], data['haematocrit'], data['haemoglobins'], data['erythrocyte'], data['leucocyte'], 
                         data['thrombocyte'], data['mch'], data['mchc'], data['mcv'], data['umur'], data['jenis_kelamin'], result))
            db.commit()
        except Exception as e:
            logging.error(f"Error during database insertion: {e}")
            db.rollback()
        finally:
            db.close()

        return render_template('classify.html', result=result, user_type=user_type, name=user_name, email=user_email, profile_picture=user_profile_picture)

    return render_template('classify.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))
    
@app.route('/patients')
def patients():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
        
    try:
        patients_df = pd.read_csv('data/patients.csv')
    except FileNotFoundError:
        patients_df = pd.DataFrame(columns=['patient_id', 'nama', 'haematocrit', 'haemoglobins', 'erythrocyte', 
                                            'leucocyte', 'thrombocyte', 'mch', 'mchc', 'mcv', 'umur', 
                                            'jenis_kelamin', 'hasil_klasifikasi'])

    return render_template('patients.html', patients_df=patients_df)

if __name__ == '__main__':
    app.run(debug=True)

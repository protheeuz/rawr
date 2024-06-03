from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response
from flask_mysqldb import MySQL
from flask_sendgrid import SendGrid
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail as SendGridMail
from werkzeug.utils import secure_filename
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
app.config['UPLOAD_FOLDER'] = './static/assets/img/admins' # folder tempat menyimpan file

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

app.config['UPLOAD_FOLDER'] = 'static/assets/img/admins'

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
    message = SendGridMail(
        from_email='matimatech@gmail.com',
        to_emails=email,
        subject='Kode Verifikasi Anda',
        plain_text_content=f'Terima kasih telah mendaftar di Sistem Klasifikasi Rekomendasi Perawatan pasien Puskesmas - Pulogadung. Kode verifikasi Anda adalah: {verification_code}'
    )
    try:
        sg = SendGridAPIClient(app.config['SENDGRID_API_KEY'])
        response = sg.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
    except Exception as e:
        print(e)

# Load or create patients data
# try:
#     patients_df = pd.read_csv('data/patients.csv')
# except FileNotFoundError:
#     patients_df = pd.DataFrame(columns=['Nama', 'HAEMATOCRIT', 'HAEMOGLOBINS', 'ERYTHROCYTE', 
#                                         'LEUCOCYTE', 'THROMBOCYTE', 'MCH', 'MCHC', 
#                                         'MCV', 'UMUR', 'JENIS_KELAMIN', 'Hasil'])

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

# ------------------------------------------------------------------------------------------------------------------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'logged_in' in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        db, cur = get_db()
        cur.execute("SELECT * FROM admins WHERE email = %s", (email,))
        admin = cur.fetchone()
        db.close()
        
        if admin:
            if hashlib.sha256(password.encode()).hexdigest() == admin['password']:
                session['logged_in'] = True
                session['admin_email'] = email
                session['admin_name'] = admin['name']
                session['admin_kualifikasi'] = admin.get('kualifikasi')
                session['admin_profil_pekerjaan'] = admin.get('profil_pekerjaan')
                session['admin_profile_picture'] = admin.get('profile_picture')
                return redirect(url_for('dashboard'))
            else:
                flash('Password salah, silakan coba lagi.', 'error')
                return redirect(url_for('login'))
        else:
            flash('Email tidak terdaftar, silakan hubungi Admin', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/admin-profile-settings', methods=['GET', 'POST'])
def admin_profile_settings():
    admin_email = session.get('admin_email')

    if not admin_email:
        flash('Email tidak tersedia di session', 'error')
        return redirect(url_for('login'))

    if request.method == 'GET':
        admin_name = session.get('admin_name')
        admin_kualifikasi = session.get('admin_kualifikasi')
        admin_profil_pekerjaan = session.get('admin_profil_pekerjaan')
        admin_profile_picture = session.get('admin_profile_picture')
        
        return render_template('admin-profile-settings.html', admin_name=admin_name, admin_email=admin_email, admin_kualifikasi=admin_kualifikasi, admin_profil_pekerjaan=admin_profil_pekerjaan, admin_profile_picture=admin_profile_picture)

    elif request.method == 'POST':
        name = request.form['name']
        kualifikasi = request.form['qualification']
        profil_pekerjaan = request.form['job']

        profile_picture = session.get('admin_profile_picture')

        # Ambil foto yang diunggah dari form
        if 'photo' in request.files:
            photo = request.files['photo']
            if photo.filename != '':
                filename = secure_filename(admin_email + os.path.splitext(photo.filename)[1])
                photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                profile_picture = filename

        try:
            db, cur = get_db()
            update_query = """
            UPDATE admins SET name = %s, kualifikasi = %s, profil_pekerjaan = %s, profile_picture = %s WHERE email = %s
            """
            cur.execute(update_query, (name, kualifikasi, profil_pekerjaan, profile_picture, admin_email))
            db.commit()

            session['admin_profile_picture'] = profile_picture  # Pastikan disimpan sebagai string

        except Exception as e:
            db.rollback()
            flash(f'Gagal memperbarui database: {e}', 'error')
        finally:
            db.close()

        session['admin_name'] = name
        session['admin_kualifikasi'] = kualifikasi
        session['admin_profil_pekerjaan'] = profil_pekerjaan

        return redirect(url_for('admin_profile_settings'))

@app.route('/dashboard', methods=['GET'])
def dashboard():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    admin_email = session.get('admin_email')

    # Ambil data admin dari database
    db, cur = get_db()
    cur.execute("SELECT * FROM admins WHERE email = %s", (admin_email,))
    admin_data = cur.fetchone()
    db.close()

    if admin_data:
        session['admin_name'] = admin_data.get('name')
        session['admin_kualifikasi'] = admin_data.get('kualifikasi')
        session['admin_profil_pekerjaan'] = admin_data.get('profil_pekerjaan')
        session['admin_profile_picture'] = admin_data.get('profile_picture').decode('utf-8') if isinstance(admin_data.get('profile_picture'), bytes) else admin_data.get('profile_picture')

    admin_name = session.get('admin_name')
    admin_kualifikasi = session.get('admin_kualifikasi')
    admin_profil_pekerjaan = session.get('admin_profil_pekerjaan')
    admin_profile_picture = session.get('admin_profile_picture')

    # Debug statements
    print(f"Admin name: {admin_name}")
    print(f"Admin profile picture (from session): {admin_profile_picture}")

    if admin_profile_picture:
        admin_profile_picture = admin_profile_picture.strip()  # Ensure no extra characters
        admin_profile_picture = url_for('static', filename=f'assets/img/admins/{admin_profile_picture}')
    else:
        admin_profile_picture = url_for('static', filename='assets/img/admins/default.png')

    logging.info(f"Admin profile picture URL: {admin_profile_picture}")
    print(admin_profile_picture, "data berhasil diload")

    # Ambil data pasien dari database
    db, cur = get_db()
    cur.execute("SELECT * FROM patients")
    patients = cur.fetchall()
    db.close()

    patients_df = pd.DataFrame(patients, columns=['id', 'nama', 'haematocrit', 'haemoglobins', 'erythrocyte', 'leucocyte', 'thrombocyte', 'mch', 'mchc', 'mcv', 'umur', 'jenis_kelamin', 'hasil_klasifikasi'])

    total_patients = len(patients_df)
    total_rujukan = len(patients_df[patients_df['hasil_klasifikasi'] == 'Rujukan Rumah Sakit'])
    total_rawat_jalan = len(patients_df[patients_df['hasil_klasifikasi'] == 'Rawat Jalan'])

    return render_template('dashboard.html', total_patients=total_patients, 
                           total_rujukan=total_rujukan, total_rawat_jalan=total_rawat_jalan,
                           admin_name=admin_name, admin_profile_picture=admin_profile_picture, 
                           admin_email=admin_email, admin_kualifikasi=admin_kualifikasi, 
                           admin_profil_pekerjaan=admin_profil_pekerjaan)

# Route untuk halaman registrasi admin
@app.route('/admin-register', methods=['GET', 'POST'])
def admin_register():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    admin_email = session.get('admin_email')
    
    if request.method == 'GET':
        admin_name = session.get('admin_name')
        admin_kualifikasi = session.get('admin_kualifikasi')
        admin_profil_pekerjaan = session.get('admin_profil_pekerjaan')
        admin_profile_picture = session.get('admin_profile_picture')
        flash_message = session.pop('admin_register_success', None)  # Ambil pesan sukses dan hapus dari session
        return render_template('admin-register.html', admin_name=admin_name, admin_email=admin_email, admin_kualifikasi=admin_kualifikasi, admin_profil_pekerjaan=admin_profil_pekerjaan, admin_profile_picture=admin_profile_picture, flash_message=flash_message)
   
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        kualifikasi = request.form['kualifikasi']
        
        # Lakukan validasi (contoh sederhana)
        if not name or not email or not password:
            flash('Semua field harus diisi.', 'error')
            return redirect(url_for('admin_register'))

        if not is_strong_password(password):
            flash('Password harus memiliki minimal 8 karakter, termasuk huruf besar, huruf kecil, angka, dan simbol.', 'error')
            return redirect(url_for('admin_register'))
        
        hashed_password = hash_password(password)
        
        db, cur = get_db()
        
        try:
            cur.execute("INSERT INTO admins (name, email, password, kualifikasi) VALUES (%s, %s, %s, %s)", (name, email, hashed_password, kualifikasi))
            db.commit()
            flash('Admin berhasil didaftarkan.', 'success')
        except MySQLdb.Error as e:
            db.rollback()
            flash(f'Terjadi kesalahan: Admin sudah tersedia.', 'error')
        finally:
            db.close()
        
        return redirect(url_for('admin_register'))
    
    return render_template('admin-register.html')

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

            db, cur = get_db()
            cur.execute("INSERT INTO admins (name, email, password) VALUES (%s, %s, %s)", (fullname, email, hash_password(password)))
            db.commit()
            db.close()

            session.pop('verification_code')
            session.pop('fullname')
            session.pop('email')
            session.pop('password')

            flash('Akun berhasil dibuat! Silakan login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Kode verifikasi tidak valid! Silakan coba lagi.', 'error')
            return redirect(url_for('verify'))

    return render_template('verify_modal.html')





@app.route('/update_admin_data', methods=['POST'])
def update_admin_data():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    admin_email = session.get('admin_email')

    name = request.form.get('name')
    kualifikasi = request.form.get('kualifikasi')
    profil_pekerjaan = request.form.get('profil_pekerjaan')

    profile_picture = None
    if 'profile_picture' in request.files:
        profile_picture_file = request.files['profile_picture']
        if profile_picture_file.filename != '':
            filename = secure_filename(admin_email + os.path.splitext(profile_picture_file.filename)[1])
            profile_picture_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            profile_picture_file.save(profile_picture_path)
            profile_picture = filename

    db, cur = get_db()
    update_query = "UPDATE admins SET name = %s, kualifikasi = %s, profil_pekerjaan = %s, profile_picture = %s WHERE email = %s"
    cur.execute(update_query, (name, kualifikasi, profil_pekerjaan, profile_picture, admin_email))
    db.commit()
    db.close()

    # Update session data
    session['admin_name'] = name
    session['admin_kualifikasi'] = kualifikasi
    session['admin_profil_pekerjaan'] = profil_pekerjaan
    if profile_picture:
        session['admin_profile_picture'] = profile_picture

    return redirect(url_for('dashboard'))


@app.route('/upload-profile-picture', methods=['GET', 'POST'])
def upload_profile_picture():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        if 'profile_picture' not in request.files:
            flash('Tidak ada file yang dipilih', 'error')
            return redirect(request.url)
        
        file = request.files['profile_picture']
        
        if file.filename == '':
            flash('Tidak ada file yang dipilih', 'error')
            return redirect(request.url)
        
        if file:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            # Update profile picture di database
            db, cur = get_db()
            cur.execute("UPDATE admins SET profile_picture = %s WHERE email = %s", (filename, session['admin_email']))
            db.commit()
            db.close()
            
            # Update session
            session['admin_profile_picture'] = filename
            
            flash('Profile picture berhasil diupload', 'success')
            return redirect(url_for('dashboard'))
    
    return render_template('upload-profile-picture.html')



@app.route('/classify', methods=['GET', 'POST'])
def classify():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    admin_email = session.get('admin_email')
    
    if request.method == 'GET':
        admin_name = session.get('admin_name')
        admin_kualifikasi = session.get('admin_kualifikasi')
        admin_profil_pekerjaan = session.get('admin_profil_pekerjaan')
        admin_profile_picture = session.get('admin_profile_picture')
        flash_message = session.pop('admin_register_success', None)  # Ambil pesan sukses dan hapus dari session
        return render_template('classify.html', admin_name=admin_name, admin_email=admin_email, admin_kualifikasi=admin_kualifikasi, admin_profil_pekerjaan=admin_profil_pekerjaan, admin_profile_picture=admin_profile_picture, flash_message=flash_message)
        
    if request.method == 'POST':
        data = request.form
        input_data = [[convert_to_float(data['haematocrit']), convert_to_float(data['haemoglobins']), convert_to_float(data['erythrocyte']),
                       convert_to_float(data['leucocyte']), convert_to_float(data['thrombocyte']), convert_to_float(data['mch']), 
                       convert_to_float(data['mchc']), convert_to_float(data['mcv']), int(data['umur']), int(data['jenis_kelamin'])]]
        
        prediction_rf = rf_model.predict(input_data)[0]

        result_rf = "Rujukan Rumah Sakit" if prediction_rf == 1 else "Rawat Jalan"

        # Simpan data pasien ke dalam database MySQL
        db, cur = get_db()
        cur.execute("INSERT INTO patients (nama, haematocrit, haemoglobins, erythrocyte, leucocyte, thrombocyte, mch, mchc, mcv, umur, jenis_kelamin, hasil_klasifikasi) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", 
                    (data['nama'], data['haematocrit'], data['haemoglobins'], data['erythrocyte'], data['leucocyte'], 
                     data['thrombocyte'], data['mch'], data['mchc'], data['mcv'], data['umur'], data['jenis_kelamin'], result_rf))
        db.commit()
        db.close()

        return render_template('classify.html', result_rf=result_rf)

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
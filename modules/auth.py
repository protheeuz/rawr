from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from itsdangerous import URLSafeTimedSerializer
import hashlib
import random
import logging
import os
import re
import MySQLdb
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail as SendGridMail
from jinja2 import Template



# Membuat Blueprint untuk Autentikasi
auth_bp = Blueprint('auth', __name__)

# Fungsi untuk mengenkripsi password
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Fungsi untuk mengirim kode verifikasi ke email
def send_verification_code(email, verification_code):
    from app import get_db, app  # Import lokal untuk menghindari circular import
    # Mengimpor `get_db` dan `app` untuk menggunakan konfigurasi dan database, tapi dilakukan secara lokal di dalam fungsi
    # untuk menghindari masalah circular import (depensi saling mengimpor satu sama lain).

    template_path = os.path.join(app.root_path, 'templates', 'verification_email.html')
    # Menentukan path untuk template email yang akan dikirim. Path ini mengarah ke file HTML template yang ada di dalam folder `templates`.

    with open(template_path, 'r') as file:
        html_template = file.read()
    # Membuka file template email (`verification_email.html`) dan membaca isinya ke dalam variabel `html_template`.

    template = Template(html_template)
    html_content = template.render(verification_code=verification_code)
    # Menggunakan `Template` dari Jinja (atau templating engine lainnya) untuk merender template dengan mengganti
    # placeholder `verification_code` dengan kode verifikasi yang akan dikirim ke email.

    message = SendGridMail(
        from_email='matimatech@gmail.com',
        to_emails=email,
        subject='Kode Verifikasi Anda',
        html_content=html_content
    )
    # Membuat pesan email menggunakan SendGrid. Mengatur pengirim, penerima, subjek, dan konten HTML yang sudah dirender.

    try:
        sg = SendGridAPIClient(app.config['SENDGRID_API_KEY'])
        response = sg.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
    except Exception as e:
        print(e)
    # Mengirimkan email menggunakan API SendGrid dengan `SENDGRID_API_KEY` yang ada di konfigurasi aplikasi (`app.config`).
    # Setelah mengirim, mencetak status code, body response, dan headers untuk debugging.
    # Jika terjadi error, error akan ditangkap dan dicetak di console.


# Fungsi untuk reset password
def send_password_reset_email(email, reset_url):
    from app import get_db, app  # Import lokal untuk menghindari circular import
    # Sama seperti fungsi sebelumnya, `get_db` dan `app` diimpor di sini untuk menghindari masalah circular import.
    
    template_path = os.path.join(app.root_path, 'templates', 'reset_password_email.html')
    logging.debug(f"Template path: {template_path}")
    # Menentukan path file template email untuk reset password dan mencetaknya untuk debugging.

    try:
        with open(template_path, 'r') as file:
            html_template = file.read()
        logging.debug("Template read successfully")
    except Exception as e:
        logging.error(f"Error reading email template: {e}")
        return
    # Membaca file template HTML (`reset_password_email.html`) yang berisi format email reset password.
    # Jika file tidak ditemukan atau ada masalah saat membaca, akan dicetak error dan fungsi akan berhenti.

    template = Template(html_template)
    html_content = template.render(reset_url=reset_url)
    logging.debug("Email content created successfully")
    # Merender template dengan menggantikan placeholder `reset_url` dengan URL untuk reset password.
    # Setelah itu, mencetak pesan debug bahwa konten email berhasil dibuat.

    message = SendGridMail(
        from_email='matimatech@gmail.com',
        to_emails=email,
        subject='Permintaan Pergantian Password',
        html_content=html_content
    )
    # Membuat objek pesan email dengan menggunakan SendGrid. Subjeknya adalah 'Permintaan Pergantian Password',
    # dan konten email yang berisi link reset password yang sudah dirender.

    try:
        sg = SendGridAPIClient(app.config['SENDGRID_API_KEY'])
        response = sg.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
    except Exception as e:
        # Mengirimkan email menggunakan SendGrid API dengan API Key yang disediakan di konfigurasi aplikasi.
        # Setelah mengirimkan, mencetak status code, body, dan headers untuk debugging.
        logging.error(f"Error sending email: {e}")
        
def is_strong_password(password):
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password): 
        return False
    if not re.search(r'[0-9]', password): 
        return False
    if not re.search(r'[\W_]', password):
        return False
    return True

# Route untuk login
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Mengecek jika user sudah login, maka akan langsung diarahkan ke halaman dashboard
    if 'logged_in' in session:
        return redirect(url_for('dashboard'))

    # Jika method request adalah POST, berarti user sedang mencoba untuk login
    if request.method == 'POST':
        email = request.form['email']  # Ambil email dari form login
        password = request.form['password']  # Ambil password dari form login

        logging.debug(f"Login attempt for email: {email}")
        from app import get_db  # Mengimpor fungsi untuk mengakses database
        db, cur = get_db()  # Mendapatkan koneksi database
        # Query untuk mencari user berdasarkan email
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()  # Ambil data user yang pertama sesuai email
        db.close()  # Menutup koneksi database

        if user:
            # Cek apakah password yang diinputkan sesuai dengan yang ada di database
            if hashlib.sha256(password.encode()).hexdigest() == user['password']:
                # Jika password benar, buat session untuk menandakan user sudah login
                session['logged_in'] = True
                session['user_id'] = user['id']  # Menyimpan id user di session
                session['user_type'] = user['role']  # Menyimpan tipe user (admin/pengunjung) di session
                session['user_email'] = email  # Menyimpan email user di session
                session['user_name'] = user['name']  # Menyimpan nama user di session
                session['user_profile_picture'] = user.get('profile_picture')  # Menyimpan foto profil user di session
                logging.debug(f"User {email} logged in successfully.")
                return redirect(url_for('dashboard'))  # Arahkan ke halaman dashboard setelah login sukses
            else:
                logging.debug("Incorrect password")
                flash('Password salah, silakan coba lagi.', 'error')  # Jika password salah, tampilkan pesan error
        else:
            logging.debug("Email tidak terdaftar")
            flash('Email tidak terdaftar, silakan hubungi Admin', 'error')  # Jika email tidak terdaftar, tampilkan pesan error

    return render_template('login.html')  # Jika request method GET atau ada masalah, render halaman login


# Route untuk registrasi
@auth_bp.route('/user-register', methods=['GET', 'POST'])
def user_register():
    # Jika request method adalah GET, tampilkan halaman registrasi dengan pesan flash jika ada
    if request.method == 'GET':
        flash_message = session.pop('user_register_success', None)  # Ambil pesan flash dari session (jika ada)
        return render_template('user-register.html', flash_message=flash_message)  # Render halaman registrasi

    # Jika request method adalah POST, proses data registrasi
    if request.method == 'POST':
        name = request.form['name']  # Ambil nama dari form
        email = request.form['email']  # Ambil email dari form
        password = request.form['password']  # Ambil password dari form

        from app import get_db  # Mengimpor fungsi untuk mengakses database
        db, cur = get_db()  # Mendapatkan koneksi ke database
        # Query untuk mencari user yang sudah terdaftar dengan email yang sama
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        existing_user = cur.fetchone()  # Ambil data user yang sesuai email
        if existing_user:
            flash('Email sudah terdaftar.', 'error')  # Jika email sudah terdaftar, tampilkan pesan error
            return redirect(url_for('auth.user_register'))  # Redirect kembali ke halaman registrasi
        db.close()  # Menutup koneksi database

        # Cek jika ada field yang kosong
        if not name or not email or not password:
            flash('Semua field harus diisi.', 'error')  # Jika ada field kosong, tampilkan pesan error
            return redirect(url_for('auth.user_register'))  # Redirect kembali ke halaman registrasi

        # Cek kekuatan password
        if not is_strong_password(password):
            flash('Password harus memiliki minimal 8 karakter, termasuk huruf besar, huruf kecil, angka, dan simbol.', 'error')
            return redirect(url_for('auth.user_register'))  # Redirect kembali ke halaman registrasi

        # Hash password sebelum disimpan
        hashed_password = hash_password(password)

        # Generate kode verifikasi 6 digit
        verification_code = ''.join(random.choices('0123456789', k=6))

        # Simpan data registrasi di session untuk digunakan di proses selanjutnya
        session['fullname'] = name
        session['email'] = email
        session['password'] = hashed_password
        session['verification_code'] = verification_code

        # Kirimkan kode verifikasi ke email
        send_verification_code(email, verification_code)

        # Berikan pesan sukses bahwa kode verifikasi sudah dikirim
        flash('Kode verifikasi telah dikirim ke email Anda. Silakan cek email Anda.', 'success')
        return redirect(url_for('auth.verify'))  # Arahkan ke halaman verifikasi setelah registrasi sukses

    # Jika request method adalah GET, tampilkan halaman registrasi
    return render_template('user-register.html')  


# Route untuk verifikasi kode
@auth_bp.route('/verify', methods=['GET', 'POST'])
def verify():
    # Jika method request adalah POST (user mengirimkan kode verifikasi)
    if request.method == 'POST':
        # Ambil kode verifikasi yang dimasukkan oleh user
        code1 = request.form.get('code1')
        code2 = request.form.get('code2')
        code3 = request.form.get('code3')
        code4 = request.form.get('code4')
        code5 = request.form.get('code5')
        code6 = request.form.get('code6')

        # Gabungkan semua kode menjadi satu string
        entered_code = f"{code1}{code2}{code3}{code4}{code5}{code6}"
        verification_code = session.get('verification_code', None)  # Ambil kode verifikasi dari session

        # Cek apakah kode yang dimasukkan cocok dengan kode verifikasi yang ada di session
        if verification_code and entered_code == verification_code:
            # Jika kode verifikasi valid, simpan data user ke database
            fullname = session.get('fullname')
            email = session.get('email')
            password = session.get('password')
            
            from app import get_db  # Mengimpor fungsi untuk mengakses database
            db, cur = get_db()  # Mendapatkan koneksi ke database
            try:
                # Menambahkan user baru ke dalam database dengan role 'pengunjung'
                cur.execute("INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, 'pengunjung')",
                            (fullname, email, password))
                db.commit()  # Commit perubahan ke database
                db.close()  # Menutup koneksi database

                # Menghapus data yang sudah ada di session setelah registrasi berhasil
                session.pop('verification_code')
                session.pop('fullname')
                session.pop('email')
                session.pop('password')

                flash('Akun berhasil dibuat! Silakan login.', 'success')  # Pesan sukses
                return redirect(url_for('auth.login'))  # Redirect ke halaman login setelah sukses

            except MySQLdb.Error as e:
                db.rollback()  # Jika terjadi error, rollback perubahan
                flash(f'Terjadi kesalahan: {e}', 'error')  # Pesan error jika query gagal

        else:
            # Jika kode verifikasi tidak valid, beri pesan error dan arahkan kembali ke halaman verifikasi
            flash('Kode verifikasi tidak valid! Silakan coba lagi.', 'error')
            return redirect(url_for('auth.verify'))

    # Jika request method adalah GET (halaman verifikasi pertama kali ditampilkan)
    return render_template('verify.html')


# Route untuk reset password
@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    # Jika request method adalah POST (user mengirimkan email untuk reset password)
    if request.method == 'POST':
        email = request.form['email']  # Ambil email yang dimasukkan oleh user

        # Cek apakah email yang dimasukkan ada di database
        db, cur = get_db()  # Mendapatkan koneksi ke database
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()  # Ambil user berdasarkan email
        db.close()  # Tutup koneksi database

        if user:
            # Jika user ditemukan, buat token untuk reset password
            token = serializer.dumps(email, salt='password-reset-salt')  # Buat token untuk email
            # Generate URL untuk reset password yang menyertakan token
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            # Kirim email berisi link reset password ke user
            send_password_reset_email(email, reset_url)
            flash('Link untuk mengatur ulang password telah dikirim ke email Anda.', 'success')
        else:
            # Jika email tidak terdaftar, beri pesan error
            flash('Email tidak terdaftar.', 'error')

        return redirect(url_for('auth.forgot_password'))  # Redirect kembali ke halaman forgot password

    # Jika request method adalah GET, tampilkan halaman forgot password
    return render_template('forgot-password.html')


# Route untuk reset password dengan token
@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        # Coba untuk mendekode token dan ambil email dari token tersebut
        email = serializer.loads(token, salt='password-reset-salt', max_age=3600)
    except:
        # Jika token tidak valid atau telah kedaluwarsa (lebih dari 1 jam), beri pesan error
        flash('Link tidak valid atau telah kedaluwarsa.', 'error')
        return redirect(url_for('auth.forgot_password'))  # Redirect ke halaman forgot password

    # Jika request method adalah POST (user mengirimkan form untuk reset password)
    if request.method == 'POST':
        new_password = request.form['password']  # Ambil password baru dari form

        # Validasi kekuatan password
        if not is_strong_password(new_password):
            flash('Password harus memiliki minimal 8 karakter, termasuk huruf besar, huruf kecil, angka, dan simbol.', 'error')
            return redirect(url_for('auth.reset_password', token=token))  # Redirect kembali ke halaman reset password jika password tidak kuat

        # Hash password baru sebelum disimpan ke database
        hashed_password = hash_password(new_password)

        # Update password di database
        db, cur = get_db()
        cur.execute("UPDATE users SET password = %s WHERE email = %s", (hashed_password, email))
        db.commit()  # Simpan perubahan
        db.close()

        flash('Password berhasil diubah. Silakan login dengan password baru Anda.', 'success')
        return redirect(url_for('auth.login'))  # Redirect ke halaman login setelah password berhasil diubah

    # Jika request method adalah GET, tampilkan halaman reset-password
    return render_template('reset-password.html')
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
    template_path = os.path.join(app.root_path, 'templates', 'verification_email.html')

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

# Fungsi untuk reset password
def send_password_reset_email(email, reset_url):
    from app import get_db, app  # Import lokal untuk menghindari circular import
    template_path = os.path.join(app.root_path, 'templates', 'reset_password_email.html')
    logging.debug(f"Template path: {template_path}")

    try:
        with open(template_path, 'r') as file:
            html_template = file.read()
        logging.debug("Template read successfully")
    except Exception as e:
        logging.error(f"Error reading email template: {e}")
        return

    template = Template(html_template)
    html_content = template.render(reset_url=reset_url)
    logging.debug("Email content created successfully")

    message = SendGridMail(
        from_email='matimatech@gmail.com',
        to_emails=email,
        subject='Permintaan Pergantian Password',
        html_content=html_content
    )

    try:
        sg = SendGridAPIClient(app.config['SENDGRID_API_KEY'])
        response = sg.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
    except Exception as e:
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
    if 'logged_in' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        logging.debug(f"Login attempt for email: {email}")
        from app import get_db
        db, cur = get_db()
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        db.close()

        if user:
            if hashlib.sha256(password.encode()).hexdigest() == user['password']:
                session['logged_in'] = True
                session['user_id'] = user['id'] 
                session['user_type'] = user['role']
                session['user_email'] = email
                session['user_name'] = user['name']
                session['user_profile_picture'] = user.get('profile_picture')
                logging.debug(f"User {email} logged in successfully.")
                return redirect(url_for('dashboard'))
            else:
                logging.debug("Incorrect password")
                flash('Password salah, silakan coba lagi.', 'error')
        else:
            logging.debug("Email tidak terdaftar")
            flash('Email tidak terdaftar, silakan hubungi Admin', 'error')

    return render_template('login.html')

# Route untuk registrasi
@auth_bp.route('/user-register', methods=['GET', 'POST'])
def user_register():
    if request.method == 'GET':
        flash_message = session.pop('user_register_success', None)
        return render_template('user-register.html', flash_message=flash_message)

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        from app import get_db
        db, cur = get_db()
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        existing_user = cur.fetchone()
        if existing_user:
            flash('Email sudah terdaftar.', 'error')
            return redirect(url_for('auth.user_register'))
        db.close()

        if not name or not email or not password:
            flash('Semua field harus diisi.', 'error')
            return redirect(url_for('auth.user_register'))

        if not is_strong_password(password):
            flash('Password harus memiliki minimal 8 karakter, termasuk huruf besar, huruf kecil, angka, dan simbol.', 'error')
            return redirect(url_for('auth.user_register'))

        hashed_password = hash_password(password)

        verification_code = ''.join(random.choices('0123456789', k=6))

        session['fullname'] = name
        session['email'] = email
        session['password'] = hashed_password
        session['verification_code'] = verification_code

        send_verification_code(email, verification_code)

        flash('Kode verifikasi telah dikirim ke email Anda. Silakan cek email Anda.', 'success')
        return redirect(url_for('auth.verify'))

    return render_template('user-register.html')

# Route untuk verifikasi kode
@auth_bp.route('/verify', methods=['GET', 'POST'])
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
            
            from app import get_db
            db, cur = get_db()
            try:
                # Set role menjadi 'pengunjung' secara eksplisit
                cur.execute("INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, 'pengunjung')",
                            (fullname, email, password))
                db.commit()
                db.close()

                session.pop('verification_code')
                session.pop('fullname')
                session.pop('email')
                session.pop('password')

                flash('Akun berhasil dibuat! Silakan login.', 'success')
                return redirect(url_for('auth.login'))
            except MySQLdb.Error as e:
                db.rollback()
                flash(f'Terjadi kesalahan: {e}', 'error')
        else:
            flash('Kode verifikasi tidak valid! Silakan coba lagi.', 'error')
            return redirect(url_for('auth.verify'))

    return render_template('verify.html')

# Route untuk reset password
@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']

        db, cur = get_db()
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        db.close()

        if user:
            token = serializer.dumps(email, salt='password-reset-salt')
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            send_password_reset_email(email, reset_url)
            flash('Link untuk mengatur ulang password telah dikirim ke email Anda.', 'success')
        else:
            flash('Email tidak terdaftar.', 'error')

        return redirect(url_for('auth.forgot_password'))

    return render_template('forgot-password.html')

# Route untuk reset password dengan token
@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=3600)
    except:
        flash('Link tidak valid atau telah kedaluwarsa.', 'error')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        new_password = request.form['password']
        if not is_strong_password(new_password):
            flash('Password harus memiliki minimal 8 karakter, termasuk huruf besar, huruf kecil, angka, dan simbol.', 'error')
            return redirect(url_for('auth.reset_password', token=token))

        hashed_password = hash_password(new_password)

        db, cur = get_db()
        cur.execute("UPDATE users SET password = %s WHERE email = %s", (hashed_password, email))
        db.commit()
        db.close()

        flash('Password berhasil diubah. Silakan login dengan password baru Anda.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('reset-password.html')
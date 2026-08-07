import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey_change_me")
DATABASE_URL = os.environ.get("DATABASE_URL")
pool = SimpleConnectionPool(1, 10, DATABASE_URL)

ADMIN_EMAIL = "jedidiah@gmail.com" # <-- CHANGE THIS TO YOUR LOGIN EMAIL ONLY

def init_db():
    conn = pool.getconn(); c = conn.cursor()
    c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE")

    # 1. Make only YOU admin
    c.execute("UPDATE users SET is_admin = TRUE WHERE email = %s", (ADMIN_EMAIL,))

    # 2. Make everyone else NOT admin
    c.execute("UPDATE users SET is_admin = FALSE WHERE email!= %s", (ADMIN_EMAIL,))

    conn.commit(); pool.putconn(conn)

def get_db(): return pool.getconn()
def release_db(conn): pool.putconn(conn)

init_db() # runs every time app starts

def get_user():
    if 'user_id' not in session: return None
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT id, name, email, is_admin FROM users WHERE id = %s", (session['user_id'],))
    user = c.fetchone(); release_db(conn)
    return {'id': user[0], 'name': user[1], 'email': user[2], 'is_admin': user[3]} if user else None

@app.route('/')
def landing():
    if 'user_id' in session:
        user = get_user()
        if user and user['is_admin']: return redirect(url_for('dashboard'))
        else: return redirect(url_for('user_app'))
    return render_template('landing.html')

# ADMIN DASHBOARD
@app.route('/dashboard')
def dashboard():
    user = get_user()
    if not user: flash("Please login first", "info"); return redirect(url_for('login'))
    if not user['is_admin']: flash("Access denied. Admin only.", "danger"); return redirect(url_for('user_app'))

    conn = get_db(); c = conn.cursor()
    c.execute("SELECT id, name, email, created_at FROM users ORDER BY id DESC")
    users = c.fetchall(); release_db(conn)
    return render_template('index.html', users=users, user_name=user['name'])

# USER DASHBOARD - BUY NUMBER + SEND SMS
@app.route('/app')
def user_app():
    user = get_user()
    if not user: flash("Please login first", "info"); return redirect(url_for('login'))
    if user['is_admin']: return redirect(url_for('dashboard')) # Admins can't use user panel

    return render_template('user_app.html', user_name=user['name'], user_email=user['email'])

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user_id' in session: return redirect(url_for('landing'))
    if request.method == 'POST':
        name, email, password = request.form.get('name'), request.form.get('email'), request.form.get('password')
        if not name or not email or not password: flash("All fields are required!", "danger"); return redirect(url_for('signup'))
        try:
            conn = get_db(); c = conn.cursor()
            c.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s)", (name, email, generate_password_hash(password)))
            conn.commit(); release_db(conn)
            flash("Account created! Please login.", "success"); return redirect(url_for('login'))
        except psycopg2.IntegrityError: flash("Email already exists!", "danger"); return redirect(url_for('signup'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        user = get_user()
        if user and user['is_admin']: return redirect(url_for('dashboard'))
        else: return redirect(url_for('user_app'))

    if request.method == 'POST':
        email, password = request.form.get('email'), request.form.get('password')
        conn = get_db(); c = conn.cursor()
        c.execute("SELECT id, name, email, password, is_admin FROM users WHERE email = %s", (email,))
        user = c.fetchone(); release_db(conn)
        if user and check_password_hash(user[3], password):
            session['user_id'], session['user_name'] = user[0], user[1]
            if user[4]: return redirect(url_for('dashboard')) # ADMIN
            else: return redirect(url_for('user_app')) # USER
        else: flash("Invalid email or password!", "danger")
    return render_template('login.html')

@app.route('/reset_password/<int:user_id>', methods=['GET', 'POST'])
def reset_password(user_id):
    admin = get_user()
    if not admin or not admin['is_admin']: return redirect(url_for('login'))

    if request.method == 'POST':
        new_pass = request.form.get('password')
        conn = get_db(); c = conn.cursor()
        c.execute("UPDATE users SET password = %s WHERE id = %s", (generate_password_hash(new_pass), user_id))
        conn.commit(); release_db(conn)
        flash("Password reset!", "success")
        return redirect(url_for('dashboard'))

    return f'''
    <body style="background:#0a0a0a;color:#e0e0e0;font-family:Segoe UI;padding:50px;text-align:center;">
    <h2 style="color:#FFD700;">Reset Password</h2>
    <form method="POST">
        <input name="password" type="text" placeholder="New Password" style="padding:10px;border-radius:5px;border:1px solid #FFD700;background:#222;color:#fff;">
        <button style="padding:10px 20px;background:#FFD700;color:#000;border:none;border-radius:5px;font-weight:bold;">RESET</button>
    </form>
    </body>
    '''

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('landing'))

@app.route('/delete_user/<int:user_id>')
def delete_user(user_id):
    user = get_user()
    if not user or not user['is_admin']: return redirect(url_for('login'))
    conn = get_db(); c = conn.cursor()
    c.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit(); release_db(conn)
    flash("User deleted!", "success")
    return redirect(url_for('dashboard'))

if __name__ == '__main__': app.run(debug=False)

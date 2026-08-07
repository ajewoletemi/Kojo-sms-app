import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey_change_me")
DATABASE_URL = os.environ.get("DATABASE_URL")
pool = SimpleConnectionPool(1, 10, DATABASE_URL)
def get_db(): return pool.getconn()
def release_db(conn): pool.putconn(conn)

def get_user():
    if 'user_id' not in session: return None
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT id, name, email, is_admin FROM users WHERE id = %s", (session['user_id'],))
    user = c.fetchone(); release_db(conn)
    return {'id': user[0], 'name': user[1], 'email': user[2], 'is_admin': user[3]} if user else None

@app.route('/')
def landing():
    if 'user_id' in session: return redirect(url_for('dashboard'))
    return render_template('landing.html')

@app.route('/dashboard')
def dashboard():
    user = get_user()
    if not user:
        flash("Please login first", "info")
        return redirect(url_for('login'))
    if not user['is_admin']:
        flash("Access denied. Admin only.", "danger")
        return redirect(url_for('logout')) # kick non-admins out
    
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT id, name, email, created_at FROM users ORDER BY id DESC")
    users = c.fetchall(); release_db(conn)
    return render_template('index.html', users=users, user_name=user['name'])

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user_id' in session: return redirect(url_for('dashboard'))
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
    if 'user_id' in session: return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email, password = request.form.get('email'), request.form.get('password')
        conn = get_db(); c = conn.cursor()
        c.execute("SELECT id, name, email, password, is_admin FROM users WHERE email = %s", (email,))
        user = c.fetchone(); release_db(conn)
        if user and check_password_hash(user[3], password):
            session['user_id'], session['user_name'] = user[0], user[1]
            if user[4]: # is_admin
                return redirect(url_for('dashboard'))
            else:
                flash("Welcome! Admin dashboard is restricted.", "info")
                return redirect(url_for('logout')) # normal users get logged out
        else: flash("Invalid email or password!", "danger")
    return render_template('login.html')

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

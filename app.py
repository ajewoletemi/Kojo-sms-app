from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "kojo_secret_key_123"

# DATABASE SETUP - FIXED
def init_db():
    conn = sqlite3.connect('kojo.db')
    c = conn.cursor()
    # This will create table if it doesn't exist, or add columns if missing
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE, password TEXT, balance REAL DEFAULT 0)''')
    conn.commit()
    conn.close()

init_db()

# HOME PAGE
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# SIGNUP
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

        conn = sqlite3.connect('kojo.db')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (name, email, password) VALUES (?,?,?)", (name, email, hashed_password))
            conn.commit()
            flash("Account created successfully! Please login.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Email already exists!", "danger")
        finally:
            conn.close()
    return render_template('signup.html')

# LOGIN - FIXED
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect('kojo.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email =?", (email,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user[3], password):
            session['user_id'] = user[0]
            session['user_name'] = user[1] if user[1] else "User" # FIX: handle if name is None
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password", "danger")
    return render_template('login.html')

# DASHBOARD - FIXED
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('kojo.db')
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE id =?", (session['user_id'],))
    result = c.fetchone()
    balance = result[0] if result else 0 # FIX: handle if no result
    conn.close()

    name = session.get('user_name', 'User') # FIX: fallback
    return render_template('dashboard.html', balance=balance, name=name)

# COMPOSE SMS PAGE
@app.route('/compose')
def compose():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('kojo.db')
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE id =?", (session['user_id'],))
    result = c.fetchone()
    balance = result[0] if result else 0
    conn.close()

    return render_template('compose.html', balance=balance)

# SEND SMS - PLACEHOLDER
@app.route('/send_sms', methods=['POST'])
def send_sms():
    numbers = request.form['numbers']
    message = request.form['message']
    flash(f"SMS would be sent to {len(numbers.split())} numbers. API coming soon!", "info")
    return redirect(url_for('compose'))

# LOGOUT
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# PLACEHOLDERS
@app.route('/fund_wallet')
def fund_wallet():
    return "Paystack Integration Coming Soon"

@app.route('/buy_number')
def buy_number():
    return "Buy Number Page Coming Soon"

if __name__ == '__main__':
    app.run(debug=True)

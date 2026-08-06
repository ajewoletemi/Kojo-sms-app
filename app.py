import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
import traceback
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import requests

app = Flask(__name__)
app.secret_key = "kojo_secret_key_123_CHANGE_THIS_LATER"

# THIS WILL PRINT THE REAL ERROR IN RENDER LOGS
@app.errorhandler(500)
def internal_error(error):
    print("=== 500 ERROR ===")
    print(traceback.format_exc())
    return "SERVER ERROR. Check Render Logs for details.", 500

# PAYSTACK KEYS
PAYSTACK_SECRET_KEY = os.environ.get("sk_test_1a831f22cc05a3c963f8b31fabc7d6c8e4c6abde")
PAYSTACK_PUBLIC_KEY = "pk_test_f36ffafee66e98c67e8d37dd1109451c4b2505" # REPLACE WITH YOUR REAL KEY

# DATABASE SETUP - SAFE VERSION FOR RENDER
def init_db():
    conn = sqlite3.connect('kojo.db')
    c = conn.cursor()
    # Create table with balance from the start
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE, password TEXT, balance REAL DEFAULT 0)''')
    
    # Try to add balance column if table already existed without it
    try:
        c.execute("ALTER TABLE users ADD COLUMN balance REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass # Column already exists, that's fine
        
    conn.commit()
    conn.close()

init_db()

# LOGIN REQUIRED DECORATOR
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please login first", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    return render_template('home.html')

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
            c.execute("INSERT INTO users (name, email, password, balance) VALUES (?,?,?,?)", (name, email, hashed_password, 0))
            conn.commit()
            flash("Account created successfully! Please login.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Email already exists", "danger")
        finally:
            conn.close()
    return render_template('signup.html')

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
            session['name'] = user[1]
            flash("Login successful", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password", "danger")
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    conn = sqlite3.connect('kojo.db')
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE id =?", (session['user_id'],))
    result = c.fetchone()
    balance = result[0] if result else 0
    conn.close()
    return render_template('dashboard.html', name=session['name'], balance=balance)

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out", "info")
    return redirect(url_for('home'))

@app.route('/fund_wallet', methods=['GET', 'POST'])
@login_required
def fund_wallet():
    if request.method == 'POST':
        amount = float(request.form['amount'])
        email = request.form['email']
        
        headers = {'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}'}
        data = {'email': email, 'amount': int(amount * 100)} # Paystack uses kobo
        
        response = requests.post('https://api.paystack.co/transaction/initialize', headers=headers, json=data)
        res_data = response.json()
        
        if res_data['status']:
            authorization_url = res_data['data']['authorization_url']
            return redirect(authorization_url)
        else:
            flash("Payment initialization failed", "danger")
            
    return render_template('fund_wallet.html', PAYSTACK_PUBLIC_KEY=PAYSTACK_PUBLIC_KEY)

@app.route('/verify_payment')
@login_required
def verify_payment():
    reference = request.args.get('reference')
    headers = {'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}'}
    response = requests.get(f'https://api.paystack.co/transaction/verify/{reference}', headers=headers)
    res_data = response.json()
    
    if res_data['status'] and res_data['data']['status'] == 'success':
        amount = res_data['data']['amount'] / 100 # Convert from kobo
        conn = sqlite3.connect('kojo.db')
        c = conn.cursor()
        c.execute("UPDATE users SET balance = balance +? WHERE id =?", (amount, session['user_id']))
        conn.commit()
        conn.close()
        flash(f"Wallet funded successfully with NGN {amount}", "success")
        return redirect(url_for('dashboard'))
    else:
        flash("Payment verification failed", "danger")
        return redirect(url_for('fund_wallet'))

if __name__ == '__main__':
    app.run(debug=True)

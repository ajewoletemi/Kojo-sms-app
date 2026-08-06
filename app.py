import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
import traceback
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import requests
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY")

PAYSTACK_SECRET_KEY = os.environ.get("PAYSTACK_SECRET_KEY")
PAYSTACK_PUBLIC_KEY = os.environ.get("PAYSTACK_PUBLIC_KEY")

@app.errorhandler(500)
def internal_error(error):
    print("=== 500 ERROR ===")
    print(traceback.format_exc())
    return "SERVER ERROR. Check Render Logs", 500

def init_db():
    conn = sqlite3.connect('kojo.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE, password TEXT, balance REAL DEFAULT 0)''')
    try:
        c.execute("ALTER TABLE users ADD COLUMN balance REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

init_db()

def login_required(f):
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
            flash("Account created! Please login.", "success")
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
    return redirect(url_for('home'))

@app.route('/fund_wallet', methods=['GET', 'POST'])
@login_required
def fund_wallet():
    if request.method == 'POST':
        amount = float(request.form['amount'])
        email = request.form['email']
        headers = {'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}'}
        data = {'email': email, 'amount': int(amount * 100), 'callback_url': url_for('verify_payment', _external=True)}
        response = requests.post('https://api.paystack.co/transaction/initialize', headers=headers, json=data)
        res_data = response.json()
        if res_data['status']:
            return redirect(res_data['data']['authorization_url'])
        else:
            flash("Payment failed", "danger")
    return render_template('fund_wallet.html', PAYSTACK_PUBLIC_KEY=PAYSTACK_PUBLIC_KEY)

@app.route('/verify_payment')
@login_required
def verify_payment():
    reference = request.args.get('reference')
    headers = {'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}'}
    response = requests.get(f'https://api.paystack.co/transaction/verify/{reference}', headers=headers)
    res_data = response.json()
    if res_data['status'] and res_data['data']['status'] == 'success':
        amount = res_data['data']['amount'] / 100
        conn = sqlite3.connect('kojo.db')
        c = conn.cursor()
        c.execute("UPDATE users SET balance = balance +? WHERE id =?", (amount, session['user_id']))
        conn.commit()
        conn.close()
        flash(f"Wallet funded with NGN {amount}", "success")
        return redirect(url_for('dashboard'))
    else:
        flash("Payment verification failed", "danger")
        return redirect(url_for('fund_wallet'))

if __name__ == '__main__':
    app.run(debug=False)

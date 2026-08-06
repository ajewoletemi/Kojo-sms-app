from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
import requests
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "kojo_secret_key_123"

PAYSTACK_SECRET_KEY = "sk_test_135f3ee265b4402656505b21a51c33b39596a1d0" # REPLACE WITH YOURS
PAYSTACK_PUBLIC_KEY = "pk_test_fa36ffafee6ee98c67e8d37dd11094f31c4b2505" # REPLACE WITH YOURS

def init_db():
    conn = sqlite3.connect('kojo.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE, password TEXT, balance REAL DEFAULT 0)''')
    conn.commit()
    conn.close()
init_db()

@app.route('/')
def index():
    if 'user_id' in session: return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name, email, password = request.form['name'], request.form['email'], request.form['password']
        hashed_password = generate_password_hash(password)
        conn = sqlite3.connect('kojo.db')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (name, email, password) VALUES (?,?,?)", (name, email, hashed_password))
            conn.commit()
            flash("Account created! Please login.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Email already exists!", "danger")
        finally: conn.close()
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email, password = request.form['email'], request.form['password']
        conn = sqlite3.connect('kojo.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email =?", (email,))
        user = c.fetchone()
        conn.close()
        if user and check_password_hash(user[3], password):
            session['user_id'], session['user_name'], session['user_email'] = user[0], user[1] or "User", user[2]
            return redirect(url_for('dashboard'))
        else: flash("Invalid email or password", "danger")
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = sqlite3.connect('kojo.db')
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE id =?", (session['user_id'],))
    balance = c.fetchone()[0]
    conn.close()
    return render_template('dashboard.html', balance=balance, name=session.get('user_name', 'User'))

@app.route('/compose')
def compose():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = sqlite3.connect('kojo.db')
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE id =?", (session['user_id'],))
    balance = c.fetchone()[0]
    conn.close()
    return render_template('compose.html', balance=balance)

# NEW: FUND WALLET PAGE
@app.route('/fund_wallet')
def fund_wallet():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = sqlite3.connect('kojo.db')
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE id =?", (session['user_id'],))
    balance = c.fetchone()[0]
    conn.close()
    return render_template('fund_wallet.html', balance=balance, email=session['user_email'], paystack_public_key=PAYSTACK_PUBLIC_KEY)

# NEW: VERIFY PAYMENT
@app.route('/verify_payment')
def verify_payment():
    reference = request.args.get('reference')
    headers = {'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}'}
    url = f'https://api.paystack.co/transaction/verify/{reference}'
    response = requests.get(url, headers=headers)
    data = response.json()

    if data['status'] and data['data']['status'] == 'success':
        amount = data['data']['amount'] / 100 # convert kobo to naira
        user_id = session['user_id']
        conn = sqlite3.connect('kojo.db')
        c = conn.cursor()
        c.execute("UPDATE users SET balance = balance +? WHERE id =?", (amount, user_id))
        conn.commit()
        conn.close()
        flash(f"Wallet funded successfully with ₦{amount}!", "success")
    else:
        flash("Payment verification failed.", "danger")
    return redirect(url_for('dashboard'))

@app.route('/send_sms', methods=['POST'])
def send_sms():
    flash("SMS API coming soon!", "info")
    return redirect(url_for('compose'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/buy_number')
def buy_number():
    return "Buy Number Page Coming Soon"

if __name__ == '__main__':
    app.run(debug=True)

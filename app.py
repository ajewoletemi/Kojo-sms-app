import os
if os.path.exists('kojo.db'):
    os.remove('kojo.db') # THIS DELETES OLD DB ON STARTUP

from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import requests
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "kojo_secret_key_123_CHANGE_THIS_LATER"

# READ KEYS
PAYSTACK_SECRET_KEY = os.environ.get("sk_test_1a831f22cc05a3c963f8b31fabc7d6c8e4c6abde")
PAYSTACK_PUBLIC_KEY = "pk_test_fa36ffafee6ee98c67e8d37dd11094f31c4b2505" 

def init_db():
    conn = sqlite3.connect('kojo.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE, password TEXT, balance REAL DEFAULT 0)''')
    # Migration: add balance column if it doesn't exist
    try:
        c.execute("ALTER TABLE users ADD COLUMN balance REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

init_db()

def get_user_data(user_id):
    """SAFE function to get user data. Returns default values if user not found"""
    conn = sqlite3.connect('kojo.db')
    c = conn.cursor()
    c.execute("SELECT id, name, email, balance FROM users WHERE id =?", (user_id,))
    user = c.fetchone()
    conn.close()
    
    if user:
        return {'id': user[0], 'name': user[1] or "User", 'email': user[2], 'balance': user[3] or 0.0}
    else:
        return None

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
    
    user = get_user_data(session['user_id'])
    if not user:
        session.clear()
        flash("Account not found. Please signup again.", "danger")
        return redirect(url_for('signup'))
        
    session['user_email'] = user['email']
    return render_template('dashboard.html', balance=user['balance'], name=user['name'])

@app.route('/compose')
def compose():
    if 'user_id' not in session: return redirect(url_for('login'))
    user = get_user_data(session['user_id'])
    if not user: return redirect(url_for('logout'))
    return render_template('compose.html', balance=user['balance'])

@app.route('/fund_wallet')
def fund_wallet():
    if 'user_id' not in session: return redirect(url_for('login'))
    user = get_user_data(session['user_id'])
    if not user:
        session.clear()
        flash("Session expired. Please login again.", "danger")
        return redirect(url_for('login'))
    return render_template('fund_wallet.html', balance=user['balance'], email=user['email'], paystack_public_key=PAYSTACK_PUBLIC_KEY)

@app.route('/verify_payment')
def verify_payment():
    if 'user_id' not in session: return redirect(url_for('login'))
    reference = request.args.get('reference')
    
    if not PAYSTACK_SECRET_KEY:
        flash("Payment Error: Secret Key not set on server.", "danger")
        return redirect(url_for('fund_wallet'))

    headers = {'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}'}
    url = f'https://api.paystack.co/transaction/verify/{reference}'
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()

        if data['status'] and data['data']['status'] == 'success':
            amount = data['data']['amount'] / 100
            user_id = session['user_id']
            conn = sqlite3.connect('kojo.db')
            c = conn.cursor()
            c.execute("UPDATE users SET balance = balance +? WHERE id =?", (amount, user_id))
            conn.commit()
            conn.close()
            flash(f"Wallet funded successfully with ₦{amount:,.2f}!", "success")
        else:
            flash("Payment verification failed.", "danger")
    except Exception as e:
        flash(f"An error occurred: {e}", "danger")
        
    return redirect(url_for('dashboard'))

@app.route('/send_sms', methods=['POST'])
def send_sms():
    flash("SMS API coming next! Let's connect Twilio.", "info")
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

import os
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, session
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from werkzeug.security import generate_password_hash, check_password_hash
from twilio.rest import Client

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey_change_me")
DATABASE_URL = os.environ.get("DATABASE_URL")
PAYSTACK_SECRET_KEY = os.environ.get("PAYSTACK_SECRET_KEY")
BTC_ADDRESS = os.environ.get("BTC_ADDRESS", "bc1qxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
TWILIO_SID = os.environ.get("TWILIO_SID")
TWILIO_TOKEN = os.environ.get("TWILIO_TOKEN")
TWILIO_FROM = os.environ.get("TWILIO_FROM")

pool = SimpleConnectionPool(1, 10, DATABASE_URL)

ADMIN_EMAIL = "jedidiah@gmail.com" # <-- ONLY YOUR EMAIL

def init_db():
    conn = pool.getconn(); c = conn.cursor()
    c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE")
    c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS wallet_balance DECIMAL(10,2) DEFAULT 0.00")

    # 1. Make only YOU admin
    c.execute("UPDATE users SET is_admin = TRUE WHERE email = %s", (ADMIN_EMAIL,))
    # 2. Make everyone else NOT admin
    c.execute("UPDATE users SET is_admin = FALSE WHERE email!= %s", (ADMIN_EMAIL,))
    conn.commit(); pool.putconn(conn)

def get_db(): return pool.getconn()
def release_db(conn): pool.putconn(conn)

init_db()

def get_user():
    if 'user_id' not in session: return None
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT id, name, email, is_admin, wallet_balance FROM users WHERE id = %s", (session['user_id'],))
    user = c.fetchone(); release_db(conn)
    return {'id': user[0], 'name': user[1], 'email': user[2], 'is_admin': user[3], 'wallet': float(user[4])} if user else None

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
    c.execute("SELECT id, name, email, created_at, wallet_balance FROM users ORDER BY id DESC")
    users = c.fetchall(); release_db(conn)
    return render_template('index.html', users=users, user_name=user['name'])

# USER DASHBOARD
@app.route('/app')
def user_app():
    user = get_user()
    if not user: flash("Please login first", "info"); return redirect(url_for('login'))
    if user['is_admin']: return redirect(url_for('dashboard'))
    return render_template('user_app.html', user_name=user['name'], wallet=user['wallet'], btc_address=BTC_ADDRESS)

# SEND SMS PAGE
@app.route('/send_sms')
def send_sms_page():
    user = get_user()
    if not user: return redirect(url_for('login'))
    if user['is_admin']: return redirect(url_for('dashboard'))
    return render_template('send_sms.html', user_name=user['name'], wallet=user['wallet'])

@app.route('/send_sms', methods=['POST'])
def send_sms_action():
    user = get_user()
    if not user: return redirect(url_for('login'))

    numbers = request.form.get('numbers').strip().split('\n')
    message = request.form.get('message')
    numbers = [n.strip() for n in numbers if n.strip()]
    cost_per_sms = 0.20
    total_cost = len(numbers) * cost_per_sms

    if user['wallet'] < total_cost:
        flash(f"Insufficient balance. Need ${total_cost:.2f}", "danger")
        return redirect(url_for('send_sms_page'))

    # Send with Twilio
    client = Client(TWILIO_SID, TWILIO_TOKEN)
    sent = 0
    for num in numbers:
        try:
            client.messages.create(body=message, from_=TWILIO_FROM, to=num)
            sent += 1
        except Exception as e:
            print(f"Failed to send to {num}: {e}")

    # Deduct wallet
    if sent > 0:
        conn = get_db(); c = conn.cursor()
        c.execute("UPDATE users SET wallet_balance = wallet_balance - %s WHERE id = %s", (sent * cost_per_sms, user['id']))
        conn.commit(); release_db(conn)

    flash(f"{sent} SMS sent! ${sent * cost_per_sms:.2f} deducted.", "success")
    return redirect(url_for('send_sms_page'))

# PAYMENT ROUTES
@app.route('/fund_card')
def fund_card():
    user = get_user()
    if not user: return redirect(url_for('login'))

    amount = 1000 # $10.00 in kobo
    headers = {'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}'}
    data = {
        'email': user['email'],
        'amount': amount,
        'callback_url': url_for('payment_callback', _external=True),
        'metadata': {'user_id': user['id']}
    }
    r = requests.post('https://api.paystack.co/transaction/initialize', json=data, headers=headers)
    res = r.json()

    if res['status']:
        return redirect(res['data']['authorization_url'])
    else:
        flash("Payment init failed", "danger")
        return redirect(url_for('user_app'))

@app.route('/fund_btc')
def fund_btc():
    user = get_user()
    if not user: return redirect(url_for('login'))
    return render_template('fund_btc.html', btc_address=BTC_ADDRESS, user_name=user['name'])

@app.route('/payment_callback')
def payment_callback():
    reference = request.args.get('reference')
    headers = {'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}'}
    r = requests.get(f'https://api.paystack.co/transaction/verify/{reference}', headers=headers)
    res = r.json()

    if res['status'] and res['data']['status'] == 'success':
        user_id = res['data']['metadata']['user_id']
        amount = res['data']['amount'] / 100 # convert kobo to dollars
        conn = get_db(); c = conn.cursor()
        c.execute("UPDATE users SET wallet_balance = wallet_balance + %s WHERE id = %s", (amount, user_id))
        conn.commit(); release_db(conn)
        flash(f"Payment successful! ${amount} credited to wallet.", "success")
    else:
        flash("Payment verification failed", "danger")
    return redirect(url_for('user_app'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user_id' in session: return redirect(url_for('landing'))
    if request.method == 'POST':
        name, email, password = request.form.get('name'), request.form.get('email'), request.form.get('password')
        if not name or not email or not password: flash("All fields required!", "danger"); return redirect(url_for('signup'))
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
            if user[4]: return redirect(url_for('dashboard'))
            else: return redirect(url_for('user_app'))
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
    return f'''<body style="background:#0a0a0a;color:#e0e0e0;font-family:Segoe UI;padding:50px;text-align:center;"><h2 style="color:#FFD700;">Reset Password</h2><form method="POST"><input name="password" type="text" placeholder="New Password" style="padding:10px;border-radius:5px;border:1px solid #FFD700;background:#222;color:#fff;"><button style="padding:10px 20px;background:#FFD700;color:#000;border:none;border-radius:5px;font-weight:bold;">RESET</button></form></body>'''

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

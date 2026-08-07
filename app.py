import os
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, session
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from werkzeug.security import generate_password_hash, check_password_hash
from twilio.rest import Client

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")
DATABASE_URL = os.environ.get("DATABASE_URL")
PAYSTACK_SECRET_KEY = os.environ.get("PAYSTACK_SECRET_KEY")
BTC_ADDRESS = os.environ.get("BTC_ADDRESS")
TWILIO_SID = os.environ.get("TWILIO_ACCOUNT_SID") 
TWILIO_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN") 
TWILIO_FROM = os.environ.get("TWILIO_PHONE_NUMBER") # <-- FIXED TO MATCH YOUR RENDER

pool = SimpleConnectionPool(1, 20, dsn=DATABASE_URL)

def get_db():
    return pool.getconn()

def release_db(conn):
    pool.putconn(conn)

def get_user():
    user_id = session.get('user_id')
    if not user_id: return None
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT id, email, wallet_balance FROM users WHERE id = %s", (user_id,))
    user = c.fetchone(); release_db(conn)
    if user: return {'id': user[0], 'email': user[1], 'wallet': float(user[2])}
    return None

@app.route('/')
def landing(): return render_template('landing.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']; password = request.form['password']
        hashed_password = generate_password_hash(password)
        conn = get_db(); c = conn.cursor()
        try:
            c.execute("INSERT INTO users (email, password) VALUES (%s, %s)", (email, hashed_password))
            conn.commit(); flash("Account created! Please login.", "success")
            return redirect(url_for('login'))
        except psycopg2.IntegrityError:
            conn.rollback(); flash("Email already exists.", "danger")
        finally: release_db(conn)
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']; password = request.form['password']
        conn = get_db(); c = conn.cursor()
        c.execute("SELECT id, password FROM users WHERE email = %s", (email,))
        user = c.fetchone(); release_db(conn)
        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]; return redirect(url_for('user_app'))
        else: flash("Invalid email or password.", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None); return redirect(url_for('landing'))

@app.route('/user_app')
def user_app():
    user = get_user()
    if not user: return redirect(url_for('login'))
    return render_template('user_app.html', user=user)

@app.route('/send_sms')
def send_sms_page():
    user = get_user()
    if not user: return redirect(url_for('login'))
    return render_template('send_sms.html', wallet=user['wallet'])

@app.route('/send_sms', methods=['POST'])
def send_sms_action():
    user = get_user()
    if not user: return redirect(url_for('login'))
    if not TWILIO_FROM:
        flash("No Twilio number set yet. Add TWILIO_PHONE_NUMBER in Render first.", "danger")
        return redirect(url_for('send_sms_page'))
    
    numbers = request.form.get('numbers').strip().split('\n')
    message = request.form.get('message')
    numbers = [n.strip() for n in numbers if n.strip()]
    cost_per_sms = 0.20
    total_cost = len(numbers) * cost_per_sms
    
    if user['wallet'] < total_cost: 
        flash(f"Insufficient balance. Need ${total_cost:.2f}", "danger")
        return redirect(url_for('send_sms_page'))
    
    client = Client(TWILIO_SID, TWILIO_TOKEN)
    sent = 0
    errors = []
    for num in numbers:
        try: 
            client.messages.create(body=message, from_=TWILIO_FROM, to=num)
            sent += 1
        except Exception as e: 
            errors.append(f"{num}: {str(e)}")
    
    if sent > 0:
        conn = get_db(); c = conn.cursor()
        c.execute("UPDATE users SET wallet_balance = wallet_balance - %s WHERE id = %s", (sent * cost_per_sms, user['id']))
        conn.commit(); release_db(conn)
        flash(f"{sent} SMS sent! ${sent * cost_per_sms:.2f} deducted.", "success")
    
    if errors:
        flash("Some failed: " + " | ".join(errors), "danger")
        
    return redirect(url_for('send_sms_page'))

@app.route('/fund_wallet')
def fund_wallet():
    user = get_user()
    if not user: return redirect(url_for('login'))
    return render_template('fund_wallet.html', user=user, btc_address=BTC_ADDRESS)

@app.route('/verify_payment', methods=['POST'])
def verify_payment():
    user = get_user()
    if not user: return redirect(url_for('login'))
    reference = request.form['reference']
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
    url = f"https://api.paystack.co/transaction/verify/{reference}"
    response = requests.get(url, headers=headers).json()
    if response.get("data", {}).get("status") == "success":
        amount = response["data"]["amount"] / 100
        conn = get_db(); c = conn.cursor()
        c.execute("UPDATE users SET wallet_balance = wallet_balance + %s WHERE id = %s", (amount, user['id']))
        conn.commit(); release_db(conn)
        flash(f"Wallet funded with ${amount:.2f}!", "success")
    else: flash("Payment verification failed.", "danger")
    return redirect(url_for('user_app'))

if __name__ == '__main__':
    app.run(debug=True)

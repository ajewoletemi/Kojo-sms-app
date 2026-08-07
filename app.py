from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import requests
import os
import uuid
from functools import wraps

app = Flask(__name__)
app.secret_key = 'kojo_secret_key_123_change_this'

PAYSTACK_SECRET_KEY = os.environ.get('PAYSTACK_SECRET_KEY')
NOWPAYMENTS_API_KEY = os.environ.get('NOWPAYMENTS_API_KEY')

NGN_TO_USD_RATE = 1500 # ₦15,000 = $10 so $1 = ₦1500
MIN_FUND_USD = 10 # $10 minimum
SMS_COST_USD = 0.20 # $0.20 per SMS - Updated for more profit
DB_PATH = '/data/database.db' # PERMANENT STORAGE

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 name TEXT NOT NULL,
                 email TEXT UNIQUE NOT NULL,
                 password TEXT NOT NULL,
                 balance_usd REAL DEFAULT 0)''')
    conn.commit()
    conn.close()
init_db()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (name, email, password) VALUES (?,?,?)", (name, email, password))
            conn.commit()
            flash('Account created! Please login')
            return redirect('/login')
        except:
            flash('Email already exists')
        conn.close()
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email =? AND password =?", (email, password))
        user = c.fetchone()
        conn.close()
        if user:
            session['user_id'] = user[0]
            session['name'] = user[1]
            session['email'] = user[2]
            return redirect('/dashboard')
        else:
            flash('Invalid login')
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT balance_usd FROM users WHERE id =?", (session['user_id'],))
    balance = c.fetchone()[0]
    conn.close()
    return render_template('dashboard.html', name=session['name'], balance=balance)

@app.route('/fund_wallet')
@login_required
def fund_wallet():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT balance_usd FROM users WHERE id =?", (session['user_id'],))
    balance = c.fetchone()[0]
    conn.close()
    min_ngn = MIN_FUND_USD * NGN_TO_USD_RATE
    return render_template('fund_wallet.html', balance=balance, min_ngn=min_ngn)

@app.route('/pay', methods=['POST'])
@login_required
def pay():
    email = request.form['email']
    amount_ngn = int(request.form['amount'])
    min_ngn = MIN_FUND_USD * NGN_TO_USD_RATE
    
    if amount_ngn < min_ngn:
        flash(f'Minimum funding is ₦{min_ngn}')
        return redirect('/fund_wallet')
        
    amount_usd = amount_ngn / NGN_TO_USD_RATE
    amount_kobo = amount_ngn * 100
    user_id = session['user_id']
    
    headers = {'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}'}
    data = {
        'email': email,
        'amount': amount_kobo,
        'callback_url': 'https://kojo-sms-app.onrender.com/callback',
        'metadata': {'user_id': user_id, 'amount_usd': amount_usd}
    }
    
    r = requests.post('https://api.paystack.co/transaction/initialize', headers=headers, json=data)
    response = r.json()
    
    if response['status']:
        return redirect(response['data']['authorization_url'])
    else:
        flash(f"Error: {response['message']}")
        return redirect('/fund_wallet')

@app.route('/callback')
def callback():
    reference = request.args.get('reference')
    headers = {'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}'}
    
    r = requests.get(f'https://api.paystack.co/transaction/verify/{reference}', headers=headers)
    response = r.json()
    
    if response['status'] and response['data']['status'] == 'success':
        amount_ngn = response['data']['amount'] / 100
        amount_usd = amount_ngn / NGN_TO_USD_RATE
        user_id = response['data']['metadata']['user_id']
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE users SET balance_usd = balance_usd +? WHERE id =?", (amount_usd, user_id))
        conn.commit()
        conn.close()
        
        flash(f'Payment Successful! ${amount_usd:.2f} added to wallet')
        return redirect('/dashboard')
    else:
        flash('Payment Verification Failed')
        return redirect('/fund_wallet')

@app.route('/fund_btc')
@login_required
def fund_btc():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT balance_usd FROM users WHERE id =?", (session['user_id'],))
    balance = c.fetchone()[0]
    conn.close()
    return render_template('fund_btc.html', balance=balance, min_usd=MIN_FUND_USD)

@app.route('/create_btc_invoice', methods=['POST'])
@login_required
def create_btc_invoice():
    amount_usd = int(request.form['amount'])
    if amount_usd < MIN_FUND_USD:
        flash(f'Minimum funding is ${MIN_FUND_USD}')
        return redirect('/fund_btc')
        
    order_id = str(uuid.uuid4())
    headers = {'x-api-key': NOWPAYMENTS_API_KEY}
    data = {
        "price_amount": amount_usd,
        "price_currency": "usd",
        "pay_currency": "btc",
        "order_id": order_id,
        "order_description": f"KOJO Wallet Topup",
        "ipn_callback_url": "https://kojo-sms-app.onrender.com/btc_webhook",
        "success_url": "https://kojo-sms-app.onrender.com/dashboard"
    }
    r = requests.post('https://api.nowpayments.io/v1/invoice', headers=headers, json=data)
    invoice = r.json()
    return redirect(invoice['invoice_url'])

@app.route('/btc_webhook', methods=['POST'])
def btc_webhook():
    data = request.json
    if data['payment_status'] == 'finished':
        order_id = data['order_id']
        amount_usd = data['price_amount']
    return '', 200

@app.route('/compose')
@login_required
def compose():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT balance_usd FROM users WHERE id =?", (session['user_id'],))
    balance = c.fetchone()[0]
    conn.close()
    return render_template('compose.html', balance=balance)

@app.route('/send_sms', methods=['POST'])
@login_required
def send_sms():
    numbers = request.form['to_number'].strip().split('\n')
    total_sms = len([n for n in numbers if n.strip()])
    total_cost = total_sms * SMS_COST_USD
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT balance_usd FROM users WHERE id =?", (session['user_id'],))
    balance = c.fetchone()[0]
    
    if balance < total_cost:
        flash(f'Insufficient Balance. You need ${total_cost:.2f} but you have ${balance:.2f}')
        conn.close()
        return redirect('/fund_wallet')
    
    c.execute("UPDATE users SET balance_usd = balance_usd -? WHERE id =?", (total_cost, session['user_id']))
    conn.commit()
    conn.close()
    
    flash(f'SMS Sent! {total_sms} messages sent. ${total_cost:.2f} deducted')
    return redirect('/dashboard')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)

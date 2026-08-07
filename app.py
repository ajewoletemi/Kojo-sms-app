from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import requests
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = 'kojo_secret_key_123_change_this' # CHANGE THIS TO SOMETHING RANDOM

PAYSTACK_SECRET_KEY = os.environ.get('PAYSTACK_SECRET_KEY')
MIN_FUND = 15000 # Minimum funding amount
SMS_COST = 4 # Cost per SMS. Change this later

# Login Required Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

# Database
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 name TEXT NOT NULL,
                 email TEXT UNIQUE NOT NULL,
                 password TEXT NOT NULL,
                 balance REAL DEFAULT 0)''')
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
        conn = sqlite3.connect('database.db')
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
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email =? AND password =?", (email, password))
        user = c.fetchone()
        conn.close()
        if user:
            session['user_id'] = user[0]
            session['name'] = user[1]
            session['email'] = user[2] # Added for fund wallet autofill
            return redirect('/dashboard')
        else:
            flash('Invalid login')
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE id =?", (session['user_id'],))
    balance = c.fetchone()[0]
    conn.close()
    return render_template('dashboard.html', name=session['name'], balance=balance)

@app.route('/fund_wallet')
@login_required
def fund_wallet():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE id =?", (session['user_id'],))
    balance = c.fetchone()[0]
    conn.close()
    return render_template('fund_wallet.html', balance=balance, min_fund=MIN_FUND)

@app.route('/pay', methods=['POST'])
@login_required
def pay():
    email = request.form['email']
    amount = int(request.form['amount'])
    
    # CHECK MINIMUM FUNDING
    if amount < MIN_FUND:
        flash(f'Minimum funding is ₦{MIN_FUND}')
        return redirect('/fund_wallet')
        
    amount_kobo = amount * 100 # Paystack uses kobo
    user_id = session['user_id']
    
    headers = {'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}'}
    data = {
        'email': email,
        'amount': amount_kobo,
        'callback_url': 'https://kojo-sms-app.onrender.com/callback',
        'metadata': {'user_id': user_id}
    }
    
    r = requests.post('https://api.paystack.co/transaction/initialize', headers=headers, json=data)
    response = r.json()
    print("PAYSTACK INIT RESPONSE:", response)
    
    if response['status']:
        return redirect(response['data']['authorization_url'])
    else:
        flash(f"Error: {response['message']}")
        return redirect('/fund_wallet')

@app.route('/callback')
def callback():
    reference = request.args.get('reference')
    print("REFERENCE:", reference) 
    print("SECRET KEY EXISTS:", bool(PAYSTACK_SECRET_KEY))
    
    if not PAYSTACK_SECRET_KEY:
        flash("Server Error: Payment key not set")
        return redirect('/fund_wallet')
    
    headers = {'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}'}
    
    r = requests.get(f'https://api.paystack.co/transaction/verify/{reference}', headers=headers)
    response = r.json()
    print("PAYSTACK VERIFY RESPONSE:", response)
    
    if response['status'] and response['data']['status'] == 'success':
        try:
            user_id = response['data']['metadata']['user_id']
        except:
            user_id = session.get('user_id') # fallback if metadata fails
            
        amount_paid = response['data']['amount'] / 100 # convert from kobo to naira
        
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("UPDATE users SET balance = balance +? WHERE id =?", (amount_paid, user_id))
        conn.commit()
        conn.close()
        
        flash(f'Payment Successful! ₦{amount_paid} added to wallet')
        return redirect('/dashboard')
    else:
        flash(f"Payment Verification Failed: {response.get('message', 'Unknown error')}")
        return redirect('/fund_wallet')

@app.route('/compose')
@login_required
def compose():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE id =?", (session['user_id'],))
    balance = c.fetchone()[0]
    conn.close()
    return render_template('compose.html', balance=balance)

@app.route('/send_sms', methods=['POST'])
@login_required
def send_sms():
    numbers = request.form['to_number'].strip().split('\n')
    message = request.form['message']
    total_sms = len([n for n in numbers if n.strip()])
    total_cost = total_sms * SMS_COST
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE id =?", (session['user_id'],))
    balance = c.fetchone()[0]
    
    # CHECK BALANCE BEFORE SENDING
    if balance < total_cost:
        flash(f'Insufficient Balance. You need ₦{total_cost} but you have ₦{balance}')
        conn.close()
        return redirect('/fund_wallet')
    
    # Deduct balance
    c.execute("UPDATE users SET balance = balance -? WHERE id =?", (total_cost, session['user_id']))
    conn.commit()
    conn.close()
    
    # TODO: Add Termii/Twilio API call here later
    flash(f'SMS Sent! {total_sms} messages sent. ₦{total_cost} deducted')
    return redirect('/dashboard')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)

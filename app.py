from flask import Flask, render_template, request, redirect, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
import requests
import uuid

app = Flask(__name__)
app.secret_key = "kojo_secret_key_123_change_this"

# DATABASE
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# PAYSTACK
PAYSTACK_SECRET_KEY = os.environ.get("PAYSTACK_SECRET_KEY")

# USER MODEL
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    wallet = db.Column(db.Float, default=0.0)
    role = db.Column(db.String(20), default='user')

with app.app_context():
    db.create_all()

# 1. HOME
@app.route('/')
def index():
    return render_template('index.html')

# 2. REGISTER
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            flash("Username already exists!", "danger")
            return redirect('/register')
            
        new_user = User(username=username, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        
        session['user'] = username
        session['role'] = 'user'
        flash("Account created!", "success")
        return redirect('/user_app')
    return render_template('register.html')

# 3. LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        
        if user:
            session['user'] = user.username
            session['role'] = user.role
            flash("Logged in!", "success")
            if user.role == 'admin':
                return redirect('/admin')
            return redirect('/user_app')
        else:
            flash("Invalid username or password", "danger")
    return render_template('login.html')

# 4. USER DASHBOARD
@app.route('/user_app')
def user_app():
    if 'user' not in session: return redirect('/login')
    user = User.query.filter_by(username=session['user']).first()
    return render_template('user_app.html', wallet=user.wallet)

# 5. ADMIN PANEL
@app.route('/admin')
def admin():
    if 'role' not in session or session['role'] != 'admin': return redirect('/')
    users = User.query.all()
    return render_template('admin.html', users=users)

# 6. FUND WALLET WITH PAYSTACK
@app.route('/fund_wallet', methods=['GET', 'POST'])
def fund_wallet():
    if 'user' not in session: return redirect('/login')
    user = User.query.filter_by(username=session['user']).first()
    
    if request.method == 'POST':
        amount = float(request.form.get('amount', 0)) or float(request.form.get('custom_amount', 0))
        if amount < 1:
            flash("Minimum amount is $1", "danger")
            return redirect('/fund_wallet')
        
        headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}", "Content-Type": "application/json"}
        data = {
            "email": user.email,
            "amount": int(amount * 100), # in cents
            "currency": "USD",
            "metadata": {"username": user.username},
            "reference": str(uuid.uuid4())
        }
        res = requests.post("https://api.paystack.co/transaction/initialize", json=data, headers=headers)
        response = res.json()
        
        if response['status']:
            return redirect(response['data']['authorization_url'])
        else:
            flash("Payment initialization failed", "danger")
            
    return render_template('fund_wallet.html', wallet=user.wallet)

# 7. PAYSTACK WEBHOOK
@app.route('/paystack/webhook', methods=['POST'])
def paystack_webhook():
    data = request.json
    if data['event'] == 'charge.success':
        username = data['data']['metadata']['username']
        amount = data['data']['amount'] / 100
        
        user = User.query.filter_by(username=username).first()
        if user:
            user.wallet += amount
            db.session.commit()
    return "OK", 200

# 8. SEND SMS
@app.route('/send_sms', methods=['GET', 'POST'])
def send_sms():
    if 'user' not in session: return redirect('/login')
    user = User.query.filter_by(username=session['user']).first()
    return render_template('send_sms.html', wallet=user.wallet)

# 9. FUND BTC
@app.route('/fund_btc')
def fund_btc():
    if 'user' not in session: return redirect('/login')
    return render_template('fund_btc.html')

# 10. LOGOUT
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)

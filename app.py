from flask import Flask, render_template, request, redirect, session, flash
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.secret_key = "kojo_secret_key_123_change_this"

# USE ENV VAR FROM RENDER - Don't hardcode password
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# USER MODEL - matches what we made in Supabase
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    wallet = db.Column(db.Float, default=0.0)
    role = db.Column(db.String(20), default='user')

# CREATE TABLES IF NOT EXISTS
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

# 6. FUND WALLET
@app.route('/fund_wallet', methods=['GET', 'POST'])
def fund_wallet():
    if 'user' not in session: return redirect('/login')
    user = User.query.filter_by(username=session['user']).first()
    
    if request.method == 'POST':
        add = float(request.form.get('amount', 0)) or float(request.form.get('custom_amount', 0))
        user.wallet += add
        db.session.commit()
        flash(f"${add} added", "success")
        return redirect('/fund_wallet')
    return render_template('fund_wallet.html', wallet=user.wallet)

# 7. SEND SMS
@app.route('/send_sms', methods=['GET', 'POST'])
def send_sms():
    if 'user' not in session: return redirect('/login')
    user = User.query.filter_by(username=session['user']).first()
    return render_template('send_sms.html', wallet=user.wallet)

# 8. FUND BTC
@app.route('/fund_btc')
def fund_btc():
    if 'user' not in session: return redirect('/login')
    return render_template('fund_btc.html')

# 9. LOGOUT
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

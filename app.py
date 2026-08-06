from flask import Flask, request, jsonify, send_from_directory, render_template, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from twilio.rest import Client
from paystackapi.paystack import Paystack
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "kojo-secret-123")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///kojo.db'
db = SQLAlchemy(app)

# INIT
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

paystack = Paystack(secret_key=os.getenv("PAYSTACK_SECRET_KEY"))
client = Client(os.getenv("TWILIO_SID"), os.getenv("TWILIO_TOKEN"))

# PRICING
SMS_RATE_NAIRA = 200
NUMBER_RATE_USD = 5

# DATABASE MODELS
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))
    wallet_balance = db.Column(db.Float, default=0.0)

class TwilioNumber(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    phone_number = db.Column(db.String(20))
    country = db.Column(db.String(10))

with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ROUTES
@app.route("/")
@login_required
def home():
    return render_template("index.html")

@app.route("/dashboard")
@login_required
def dashboard():
    numbers = TwilioNumber.query.filter_by(user_id=current_user.id).all()
    return render_template("dashboard.html", balance=current_user.wallet_balance, numbers=numbers)

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        new_user = User(email=email, password=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for("login"))
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(email=request.form.get("email")).first()
        if user and check_password_hash(user.password, request.form.get("password")):
            login_user(user)
            return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/buy-number", methods=["POST"])
@login_required
def buy_number():
    country = request.form.get("country") # US, NG, GB
    if current_user.wallet_balance < (NUMBER_RATE_USD * 800): # rough $1 = ₦800
        return "Insufficient balance", 400

    # BUY FROM TWILIO
    available = client.available_phone_numbers(country).local.list(limit=1)
    if not available: return "No numbers available", 400
    purchased = client.incoming_phone_numbers.create(phone_number=available[0].phone_number)

    # SAVE & DEDUCT
    new_num = TwilioNumber(user_id=current_user.id, phone_number=purchased.phone_number, country=country)
    db.session.add(new_num)
    current_user.wallet_balance -= (NUMBER_RATE_USD * 800)
    db.session.commit()
    return redirect(url_for("dashboard"))

@app.route("/send-sms", methods=["POST"])
@login_required
def send_sms():
    data = request.json
    numbers = data.get("to").split(",")
    message = data.get("message")
    cost = len(numbers) * SMS_RATE_NAIRA

    if current_user.wallet_balance < cost:
        return jsonify({"error": "Low wallet balance"}), 400

    # DEDUCT FIRST
    current_user.wallet_balance -= cost
    db.session.commit()

    # SEND FROM USER'S FIRST NUMBER
    user_num = TwilioNumber.query.filter_by(user_id=current_user.id).first()
    if not user_num: return jsonify({"error": "Buy a number first"}), 400

    for num in numbers:
        client.messages.create(to=num.strip(), from_=user_num.phone_number, body=message)

    return jsonify({"status": f"Sent {len(numbers)} SMS. Charged ₦{cost}"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

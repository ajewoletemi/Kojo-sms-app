import os
import uuid
import requests
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from supabase import create_client, Client

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or os.environ.get("SECRET_KEY") or "change-this-in-production"

# Database (Supabase / Postgres via SQLAlchemy)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ========== CONFIG ==========
PAYSTACK_SECRET = os.environ.get("PAYSTACK_SECRET_KEY")
TWILIO_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE = os.environ.get("TWILIO_PHONE_NUMBER")
BTC_ADDRESS = os.environ.get("BITCOIN_WALLET_ADDRESS")

# Supabase Client (for user_numbers + inbox tables)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")  # service_role key
supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

COST_PER_SMS = 0.20          # USD
COST_VIRTUAL_NUMBER = 5.00   # USD
NGN_TO_USD_RATE = 1500       # ₦1500 = $1  →  ₦15,000 = $10
MIN_FUND_USD = 10.00

twilio_client = None
if TWILIO_SID and TWILIO_TOKEN:
    twilio_client = Client(TWILIO_SID, TWILIO_TOKEN)

# ========== MODELS (still used for users, transactions, btc) ==========
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    wallet = db.Column(db.Float, default=0.0)
    role = db.Column(db.String(20), default="user")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    transactions = db.relationship("Transaction", backref="user", lazy=True)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    type = db.Column(db.String(30))
    amount = db.Column(db.Float)
    status = db.Column(db.String(20), default="pending")
    reference = db.Column(db.String(100))
    meta = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class BTCRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    amount_usd = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship("User", backref="btc_requests")

with app.app_context():
    db.create_all()

# ========== HELPERS ==========
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first", "danger")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Admin access required", "danger")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated

def get_current_user():
    if "user_id" in session:
        return User.query.get(session["user_id"])
    return None

# ========== AUTH ==========
@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not username or not email or not password:
            flash("All fields are required", "danger")
            return redirect(url_for("register"))

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash("Username or email already exists", "danger")
            return redirect(url_for("register"))

        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()

        session["user_id"] = user.id
        session["username"] = user.username
        session["role"] = user.role
        flash("Account created successfully!", "success")
        return redirect(url_for("dashboard"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login_id = request.form.get("username") or request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter(
            (User.username == login_id) | (User.email == login_id)
        ).first()

        if user and check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role
            flash(f"Welcome back, {user.username}!", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid credentials", "danger")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully", "info")
    return redirect(url_for("index"))

# ========== DASHBOARD ==========
@app.route("/dashboard")
@app.route("/user_app")
@login_required
def dashboard():
    user = get_current_user()

    # Get numbers from Supabase user_numbers table
    numbers = []
    if supabase:
        try:
            res = supabase.table("user_numbers").select("*").eq("user_id", str(user.id)).execute()
            numbers = res.data or []
        except Exception as e:
            print("Error fetching numbers:", e)

    return render_template(
        "user_app.html",
        user=user,
        wallet=user.wallet,
        numbers=numbers,
        recent_msgs=[]
    )

# ========== FUND WITH PAYSTACK ==========
@app.route("/fund_wallet", methods=["GET", "POST"])
@login_required
def fund_wallet():
    user = get_current_user()
    if request.method == "POST":
        try:
            amount_ngn = float(request.form.get("amount", 0))
        except:
            flash("Invalid amount", "danger")
            return redirect(url_for("fund_wallet"))

        if amount_ngn < 15000:
            flash("Minimum funding is ₦15,000 ($10)", "danger")
            return redirect(url_for("fund_wallet"))

        amount_usd = round(amount_ngn / NGN_TO_USD_RATE, 2)
        reference = str(uuid.uuid4())

        tx = Transaction(
            user_id=user.id,
            type="fund_paystack",
            amount=amount_usd,
            status="pending",
            reference=reference,
            meta=f"NGN {amount_ngn}"
        )
        db.session.add(tx)
        db.session.commit()

        headers = {
            "Authorization": f"Bearer {PAYSTACK_SECRET}",
            "Content-Type": "application/json"
        }
        data = {
            "email": user.email,
            "amount": int(amount_ngn * 100),
            "currency": "NGN",
            "reference": reference,
            "metadata": {
                "user_id": user.id,
                "username": user.username,
                "usd_amount": amount_usd
            },
            "callback_url": url_for("paystack_callback", _external=True)
        }

        try:
            res = requests.post(
                "https://api.paystack.co/transaction/initialize",
                json=data, headers=headers, timeout=20
            )
            result = res.json()
            if result.get("status"):
                return redirect(result["data"]["authorization_url"])
            else:
                flash("Payment init failed: " + result.get("message", "Unknown error"), "danger")
        except Exception as e:
            flash(f"Payment error: {str(e)}", "danger")

    return render_template("fund_wallet.html", wallet=user.wallet, user=user)

@app.route("/paystack/callback")
@login_required
def paystack_callback():
    reference = request.args.get("reference")
    if not reference:
        flash("No reference provided", "danger")
        return redirect(url_for("dashboard"))

    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET}"}
    try:
        res = requests.get(
            f"https://api.paystack.co/transaction/verify/{reference}",
            headers=headers, timeout=15
        )
        result = res.json()

        if result.get("status") and result["data"]["status"] == "success":
            tx = Transaction.query.filter_by(reference=reference, status="pending").first()
            if tx:
                user = User.query.get(tx.user_id)
                user.wallet += tx.amount
                tx.status = "completed"
                db.session.commit()
                flash(f"Successfully funded ${tx.amount:.2f}!", "success")
            else:
                flash("Transaction already processed or not found", "warning")
        else:
            flash("Payment verification failed", "danger")
    except Exception as e:
        flash(f"Verification error: {str(e)}", "danger")

    return redirect(url_for("dashboard"))

@app.route("/paystack/webhook", methods=["POST"])
def paystack_webhook():
    data = request.get_json(silent=True)
    if data and data.get("event") == "charge.success":
        reference = data["data"].get("reference")
        tx = Transaction.query.filter_by(reference=reference, status="pending").first()
        if tx:
            user = User.query.get(tx.user_id)
            user.wallet += tx.amount
            tx.status = "completed"
            db.session.commit()
    return "OK", 200

# ========== FUND WITH BTC ==========
@app.route("/fund_btc", methods=["GET", "POST"])
@login_required
def fund_btc():
    user = get_current_user()
    if request.method == "POST":
        try:
            amount = float(request.form.get("amount", 0))
        except:
            flash("Invalid amount", "danger")
            return redirect(url_for("fund_btc"))

        if amount < MIN_FUND_USD:
            flash(f"Minimum BTC funding is ${MIN_FUND_USD}", "danger")
            return redirect(url_for("fund_btc"))

        req = BTCRequest(user_id=user.id, amount_usd=amount)
        db.session.add(req)
        db.session.commit()
        flash("Payment request submitted. Admin will credit your wallet after confirmation.", "info")
        return redirect(url_for("dashboard"))

    return render_template(
        "fund_btc.html",
        btc_address=BTC_ADDRESS,
        min_usd=MIN_FUND_USD,
        wallet=user.wallet
    )

# ========== BUY VIRTUAL NUMBER (UPDATED - uses user_numbers table) ==========
@app.route("/buy_number", methods=["GET", "POST"])
@login_required
def buy_number():
    user = get_current_user()

    if request.method == "POST":
        if not twilio_client:
            flash("Twilio is not configured", "danger")
            return redirect(url_for("buy_number"))

        if not supabase:
            flash("Supabase is not configured", "danger")
            return redirect(url_for("buy_number"))

        if user.wallet < COST_VIRTUAL_NUMBER:
            flash("Insufficient balance. You need $5.00", "danger")
            return redirect(url_for("buy_number"))

        country = request.form.get("country", "US")
        try:
            available = twilio_client.available_phone_numbers(country).local.list(limit=5)
            if not available:
                flash("No numbers currently available in that country", "danger")
                return redirect(url_for("buy_number"))

            number_to_buy = available[0].phone_number

            # Buy the number on Twilio
            incoming = twilio_client.incoming_phone_numbers.create(
                phone_number=number_to_buy,
                sms_url=url_for("twilio_incoming", _external=True),
                sms_method="POST"
            )

            # Deduct from wallet
            user.wallet -= COST_VIRTUAL_NUMBER
            db.session.commit()

            # Insert into Supabase user_numbers table
            supabase.table("user_numbers").insert({
                "user_id": str(user.id),
                "phone_number": incoming.phone_number,
                "twilio_sid": incoming.sid,
                "country": country
            }).execute()

            # Log transaction
            tx = Transaction(
                user_id=user.id,
                type="buy_number",
                amount=COST_VIRTUAL_NUMBER,
                status="completed",
                reference=incoming.sid,
                meta=incoming.phone_number
            )
            db.session.add(tx)
            db.session.commit()

            flash(f"Successfully purchased {incoming.phone_number}!", "success")
            return redirect(url_for("my_numbers"))

        except Exception as e:
            flash(f"Error: {str(e)}", "danger")

    return render_template("buy_number.html", cost=COST_VIRTUAL_NUMBER, wallet=user.wallet)

@app.route("/my_numbers")
@login_required
def my_numbers():
    user = get_current_user()
    numbers = []
    if supabase:
        try:
            res = supabase.table("user_numbers").select("*").eq("user_id", str(user.id)).order("created_at", desc=True).execute()
            numbers = res.data or []
        except Exception as e:
            print("Error fetching numbers:", e)
            flash("Could not load numbers", "danger")

    return render_template("my_numbers.html", numbers=numbers, wallet=user.wallet)

# ========== SEND SMS ==========
@app.route("/send_sms", methods=["GET", "POST"])
@login_required
def send_sms():
    user = get_current_user()

    # Get user's numbers from Supabase
    numbers = []
    if supabase:
        try:
            res = supabase.table("user_numbers").select("*").eq("user_id", str(user.id)).execute()
            numbers = res.data or []
        except:
            pass

    if request.method == "POST":
        if not twilio_client:
            flash("Twilio is not configured", "danger")
            return redirect(url_for("send_sms"))

        recipients_raw = request.form.get("recipients", "")
        message = request.form.get("message", "").strip()
        from_number = request.form.get("from_number") or TWILIO_PHONE

        recipients = [r.strip() for r in recipients_raw.splitlines() if r.strip()]
        if not recipients or not message:
            flash("Recipients and message are required", "danger")
            return redirect(url_for("send_sms"))

        total_cost = len(recipients) * COST_PER_SMS
        if user.wallet < total_cost:
            flash(f"Insufficient balance. Need ${total_cost:.2f}", "danger")
            return redirect(url_for("send_sms"))

        success_count = 0
        for num in recipients:
            try:
                msg = twilio_client.messages.create(
                    body=message,
                    from_=from_number,
                    to=num
                )
                success_count += 1
            except Exception as e:
                print(f"Failed to send to {num}: {e}")

        user.wallet -= success_count * COST_PER_SMS
        db.session.add(Transaction(
            user_id=user.id,
            type="send_sms",
            amount=success_count * COST_PER_SMS,
            status="completed",
            meta=f"{success_count} messages"
        ))
        db.session.commit()

        flash(f"Sent {success_count}/{len(recipients)} messages. Cost: ${success_count * COST_PER_SMS:.2f}", "success")
        return redirect(url_for("sent_messages"))

    return render_template(
        "send_sms.html",
        wallet=user.wallet,
        numbers=numbers,
        cost_per_sms=COST_PER_SMS
    )

# ========== INBOX (reads from new inbox table) ==========
@app.route("/inbox")
@login_required
def inbox():
    user = get_current_user()
    messages = []
    if supabase:
        try:
            res = supabase.table("inbox")\
                .select("*")\
                .eq("user_id", str(user.id))\
                .order("created_at", desc=True)\
                .limit(100)\
                .execute()
            messages = res.data or []
        except Exception as e:
            print("Inbox error:", e)

    return render_template("inbox.html", messages=messages, wallet=user.wallet)

@app.route("/sent")
@login_required
def sent_messages():
    user = get_current_user()
    # For now we keep sent messages simple (you can expand later)
    return render_template("sent.html", messages=[], wallet=user.wallet)

# ========== TWILIO INCOMING WEBHOOK (UPDATED - uses inbox table) ==========
@app.route("/twilio/incoming", methods=["POST"])
def twilio_incoming():
    from_number = request.form.get("From")
    to_number = request.form.get("To")
    body = request.form.get("Body", "")
    sms_sid = request.form.get("MessageSid", "")

    if supabase:
        try:
            # Find owner of the number
            result = supabase.table("user_numbers")\
                .select("user_id")\
                .eq("phone_number", to_number)\
                .execute()

            if result.data:
                user_id = result.data[0]["user_id"]

                # Save to inbox table
                supabase.table("inbox").insert({
                    "user_id": user_id,
                    "from_number": from_number,
                    "to_number": to_number,
                    "message": body,
                    "sms_sid": sms_sid,
                    "read": False
                }).execute()
        except Exception as e:
            print("Twilio incoming error:", str(e))

    # Always return empty TwiML so Twilio is happy
    resp = MessagingResponse()
    return str(resp)

# ========== ADMIN ==========
@app.route("/admin")
@login_required
@admin_required
def admin():
    users = User.query.order_by(User.created_at.desc()).all()
    pending_btc = BTCRequest.query.filter_by(status="pending").order_by(BTCRequest.created_at.desc()).all()
    return render_template("admin.html", users=users, pending_btc=pending_btc)

@app.route("/admin/approve_btc/<int:req_id>")
@login_required
@admin_required
def approve_btc(req_id):
    req = BTCRequest.query.get_or_404(req_id)
    if req.status != "pending":
        flash("Already processed", "warning")
        return redirect(url_for("admin"))

    user = User.query.get(req.user_id)
    user.wallet += req.amount_usd
    req.status = "approved"

    db.session.add(Transaction(
        user_id=user.id,
        type="fund_btc",
        amount=req.amount_usd,
        status="completed",
        reference=f"btc-{req.id}"
    ))
    db.session.commit()
    flash(f"Approved ${req.amount_usd:.2f} for {user.username}", "success")
    return redirect(url_for("admin"))

@app.route("/admin/reject_btc/<int:req_id>")
@login_required
@admin_required
def reject_btc(req_id):
    req = BTCRequest.query.get_or_404(req_id)
    req.status = "rejected"
    db.session.commit()
    flash("Request rejected", "info")
    return redirect(url_for("admin"))

# One-time admin creator
@app.route("/create_first_admin", methods=["GET", "POST"])
def create_first_admin():
    if User.query.filter_by(role="admin").first():
        flash("Admin already exists", "warning")
        return redirect(url_for("login"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not username or not email or not password:
            flash("All fields required", "danger")
            return redirect(url_for("create_first_admin"))

        admin = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            role="admin",
            wallet=0.0
        )
        db.session.add(admin)
        db.session.commit()
        flash("Admin created successfully! You can now log in.", "success")
        return redirect(url_for("login"))

    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Create Admin</title>
        <style>
            body { background:#0b0b0b; color:#fff; font-family:sans-serif; display:flex; justify-content:center; align-items:center; height:100vh; margin:0; }
            form { background:#161616; padding:30px; border-radius:16px; width:320px; }
            input { width:100%; padding:12px; margin:8px 0 16px; border-radius:8px; border:1px solid #333; background:#111; color:#fff; }
            button { width:100%; padding:12px; background:#ffcc00; border:none; border-radius:8px; font-weight:bold; cursor:pointer; }
            h2 { color:#ffcc00; text-align:center; }
        </style>
    </head>
    <body>
        <form method="post">
            <h2>Create First Admin</h2>
            <input name="username" placeholder="Username" required>
            <input name="email" type="email" placeholder="Email" required>
            <input name="password" type="password" placeholder="Password" required>
            <button type="submit">Create Admin</button>
        </form>
    </body>
    </html>
    """

# ========== RUN ==========
if __name__ == "__main__":
    app.run(debug=False)

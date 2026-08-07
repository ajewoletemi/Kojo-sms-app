from flask import Flask, render_template, request, redirect, session, flash

app = Flask(__name__)
app.secret_key = "kojo_secret_key_123"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['user'] = request.form['username']
        flash("Logged in successfully!", "success")
        return redirect('/user_app')
    return render_template('login.html')

@app.route('/user_app')
def user_app():
    if 'user' not in session:
        return redirect('/login')
    wallet_balance = 0.0 
    return render_template('user_app.html', wallet=wallet_balance)

@app.route('/send_sms', methods=['GET', 'POST'])
def send_sms():
    if 'user' not in session:
        return redirect('/login')
    wallet_balance = 0.0

    if request.method == 'POST':
        numbers = request.form['numbers'].splitlines()
        numbers = [n.strip() for n in numbers if n.strip()]
        flash(f"SMS Queued to {len(numbers)} numbers. Demo mode.", "success")
        return redirect('/user_app')

    return render_template('send_sms.html', wallet=wallet_balance)

@app.route('/fund_wallet')
def fund_wallet():
    return render_template('fund_wallet.html')

@app.route('/fund_btc')
def fund_btc():
    return render_template('fund_btc.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("Logged out", "info")
    return redirect('/')

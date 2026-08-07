from flask import Flask, render_template, request, redirect, session, flash

app = Flask(__name__)
app.secret_key = "kojo_secret_key_123_change_this_later"

# ROUTE 1: WELCOME PAGE
@app.route('/')
def index():
    return render_template('index.html')

# ROUTE 2: LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # For now: any username + password works. We will add real DB later
        session['user'] = username
        flash("Logged in successfully!", "success")
        return redirect('/user_app')
    return render_template('login.html')

# ROUTE 3: DASHBOARD
@app.route('/user_app')
def user_app():
    if 'user' not in session:
        flash("Please login first", "warning")
        return redirect('/login')
    wallet_balance = 0.0 
    return render_template('user_app.html', wallet=wallet_balance)

# ROUTE 4: SEND SMS
@app.route('/send_sms', methods=['GET', 'POST'])
def send_sms():
    if 'user' not in session:
        flash("Please login first", "warning")
        return redirect('/login')
    wallet_balance = 0.0

    if request.method == 'POST':
        numbers = request.form['numbers'].splitlines()
        numbers = [n.strip() for n in numbers if n.strip()]
        message = request.form['message']
        flash(f"SMS Queued to {len(numbers)} numbers. Demo mode.", "success")
        return redirect('/user_app')

    return render_template('send_sms.html', wallet=wallet_balance)

# ROUTE 5: FUND WITH CARD
@app.route('/fund_wallet')
def fund_wallet():
    if 'user' not in session:
        return redirect('/login')
    wallet_balance = 0.0
    return render_template('fund_wallet.html', wallet=wallet_balance)

# ROUTE 6: FUND WITH BTC
@app.route('/fund_btc')
def fund_btc():
    if 'user' not in session:
        return redirect('/login')
    return render_template('fund_btc.html')

# ROUTE 7: LOGOUT
@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("Logged out", "info")
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)

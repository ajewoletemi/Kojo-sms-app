from flask import Flask, render_template, request, redirect, session, flash

app = Flask(__name__)
app.secret_key = "kojo_secret_key_123_change_this_later"

# SIMPLE USER STORAGE - just for demo. We will use database later
users = {} 

# ROUTE 1: WELCOME PAGE
@app.route('/')
def index():
    return render_template('index.html')

# ROUTE 2: REGISTER
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if username in users:
            flash("Username already exists!", "danger")
            return redirect('/register')

        # Save user
        users[username] = {'email': email, 'password': password, 'wallet': 0.0}
        session['user'] = username
        session['wallet'] = 0.0
        flash("Account created successfully!", "success")
        return redirect('/user_app')
    return render_template('register.html')

# ROUTE 3: LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username in users and users[username]['password'] == password:
            session['user'] = username
            session['wallet'] = users[username]['wallet']
            flash("Logged in successfully!", "success")
            return redirect('/user_app')
        else:
            flash("Invalid username or password", "danger")
    return render_template('login.html')

# ROUTE 4: DASHBOARD
@app.route('/user_app')
def user_app():
    if 'user' not in session:
        flash("Please login first", "warning")
        return redirect('/login')
    username = session['user']
    wallet_balance = users[username]['wallet']
    return render_template('user_app.html', wallet=wallet_balance)

# ROUTE 5: SEND SMS
@app.route('/send_sms', methods=['GET', 'POST'])
def send_sms():
    if 'user' not in session:
        flash("Please login first", "warning")
        return redirect('/login')
    username = session['user']
    wallet_balance = users[username]['wallet']

    if request.method == 'POST':
        numbers = request.form['numbers'].splitlines()
        numbers = [n.strip() for n in numbers if n.strip()]
        flash(f"SMS Queued to {len(numbers)} numbers. Demo mode.", "success")
        return redirect('/user_app')

    return render_template('send_sms.html', wallet=wallet_balance)

# ROUTE 6: FUND WITH CARD
@app.route('/fund_wallet', methods=['GET', 'POST'])
def fund_wallet():
    if 'user' not in session:
        return redirect('/login')
    
    username = session['user']
    wallet_balance = users[username]['wallet']

    if request.method == 'POST':
        if 'amount' in request.form:
            add_amount = float(request.form['amount'])
        elif 'custom_amount' in request.form and request.form['custom_amount']:
            add_amount = float(request.form['custom_amount'])
        else:
            add_amount = 0

        users[username]['wallet'] += add_amount
        session['wallet'] = users[username]['wallet']
        flash(f"${add_amount} added to wallet successfully!", "success")
        return redirect('/fund_wallet')

    return render_template('fund_wallet.html', wallet=wallet_balance)

# ROUTE 7: FUND WITH BTC
@app.route('/fund_btc')
def fund_btc():
    if 'user' not in session:
        return redirect('/login')
    return render_template('fund_btc.html')

# ROUTE 8: LOGOUT
@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('wallet', None)
    flash("Logged out", "info")
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)

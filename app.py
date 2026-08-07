from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = "kojo_secret_key_123" # Change this later

# Dummy login for now
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['user'] = request.form['username']
        return redirect('/user_app')
    return '''
    <form method="post">
        <input name="username" placeholder="Username">
        <input name="password" type="password" placeholder="Password">
        <button type="submit">Login</button>
    </form>
    '''

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
        from_number = request.form['from_number']
        numbers = request.form['numbers'].splitlines()
        message = request.form['message']
        numbers = [n.strip() for n in numbers if n.strip()]
        
        flash(f"SMS Queued to {len(numbers)} numbers. This is a demo.", "success")
        return redirect('/user_app')

    return render_template('send_sms.html', wallet=wallet_balance)

@app.route('/fund_wallet')
def fund_wallet():
    return "<h2>Fund Wallet Page - Coming Soon</h2><a href='/user_app'>Back</a>"

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True)

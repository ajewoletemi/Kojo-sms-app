@app.route('/user_app')
def user_app():
    if 'user' not in session:
        return redirect('/login')
    # Later we will pull this from DB. For now 0.0
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
        
        # Filter empty lines
        numbers = [n.strip() for n in numbers if n.strip()]
        
        flash(f"SMS Queued to {len(numbers)} numbers. This is a demo.", "success")
        return redirect('/user_app')

    return render_template('send_sms.html', wallet=wallet_balance)

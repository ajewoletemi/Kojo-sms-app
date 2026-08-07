# ... same code as before ...

@app.route('/send_sms', methods=['POST'])
def send_sms_action():
    user = get_user()
    if not user: return redirect(url_for('login'))
    if not TWILIO_FROM:
        flash("No Twilio number set yet. Add TWILIO_FROM in Render first.", "danger")
        return redirect(url_for('send_sms_page'))
    
    numbers = request.form.get('numbers').strip().split('\n')
    message = request.form.get('message')
    numbers = [n.strip() for n in numbers if n.strip()]
    cost_per_sms = 0.20
    total_cost = len(numbers) * cost_per_sms
    
    if user['wallet'] < total_cost: 
        flash(f"Insufficient balance. Need ${total_cost:.2f}", "danger")
        return redirect(url_for('send_sms_page'))
    
    client = Client(TWILIO_SID, TWILIO_TOKEN)
    sent = 0
    errors = []
    for num in numbers:
        try: 
            client.messages.create(body=message, from_=TWILIO_FROM, to=num)
            sent += 1
        except Exception as e: 
            errors.append(f"{num}: {str(e)}")
    
    if sent > 0:
        conn = get_db(); c = conn.cursor()
        c.execute("UPDATE users SET wallet_balance = wallet_balance - %s WHERE id = %s", (sent * cost_per_sms, user['id']))
        conn.commit(); release_db(conn)
        flash(f"{sent} SMS sent! ${sent * cost_per_sms:.2f} deducted.", "success")
    
    if errors:
        flash("Some failed: " + " | ".join(errors), "danger")
        
    return redirect(url_for('send_sms_page'))

# ... rest of code same ...

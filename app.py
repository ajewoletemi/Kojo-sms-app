from flask import Flask, render_template, request, jsonify
from twilio.rest import Client
import os

app = Flask(__name__, template_folder='Templates')

# Get keys from Render Environment Variables
account_sid = os.environ.get('TWILIO_SID')
auth_token = os.environ.get('TWILIO_TOKEN')
twilio_number = os.environ.get('TWILIO_NUMBER')

@app.route('/', methods=['GET'])
def home():
    return render_template('index.html')

@app.route('/send_sms', methods=['POST'])
def send_sms():
    message = request.form.get('message')
    numbers = request.form.get('number')
    
    # Split numbers by comma
    number_list = [num.strip() for num in numbers.split(',')]
    
    client = Client(account_sid, auth_token)
    sent = []
    
    for num in number_list:
        try:
            client.messages.create(
                body=message,
                from_=twilio_number,
                to=num
            )
            sent.append(num)
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)})
    
    return jsonify({"status": "success", "message": f"SMS sent to {len(sent)} numbers"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

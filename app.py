from flask import Flask, request, jsonify
from twilio.rest import Client
import os

app = Flask(__name__)

@app.route('/send-sms', methods=['POST'])
def send_sms():
    data = request.json
    to_number = data['to']
    message_body = data['message']
    
    account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
    from_number = os.environ.get('TWILIO_PHONE_NUMBER')
    
    client = Client(account_sid, auth_token)
    message = client.messages.create(
        body=message_body,
        from_=from_number,
        to=to_number
    )
    return jsonify({"sid": message.sid, "status": "sent"})

if __name__ == '__main__':
    app.run()

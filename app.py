from flask import Flask, request, jsonify, send_from_directory
from twilio.rest import Client
import os

app = Flask(__name__)

# GET THESE FROM RENDER ENVIRONMENT VARIABLES
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN") 
TWILIO_FROM = os.getenv("TWILIO_FROM") # e.g +17372508034

client = Client(TWILIO_SID, TWILIO_TOKEN)

# THIS ONE GO SHOW YOUR DASHBOARD WHEN YOU OPEN THE URL
@app.route("/")
def home():
    return send_from_directory("Templates", "index.html")

# THIS ONE NA THE SEND SMS ROUTE
@app.route("/send-sms", methods=["POST"])
def send_sms():
    data = request.json
    to_number = data.get("to")
    message_body = data.get("message")
    
    if not to_number or not message_body:
        return jsonify({"error": "Missing to or message"}), 400
    
    try:
        message = client.messages.create(
            to=to_number,
            from_=TWILIO_FROM,
            body=message_body
        )
        return jsonify({"status": "sent", "sid": message.sid})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

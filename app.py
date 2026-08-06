
from flask import Flask, render_template, request, jsonify
import os

app = Flask(__name__, template_folder='Templates')

@app.route('/', methods=['GET'])
def home():
    return render_template('index.html')

@app.route('/send_sms', methods=['POST'])
def send_sms():
    message = request.form.get('message')
    number = request.form.get('number')
    # Fake for now - we go add Twilio later
    return jsonify({"status": "success", "message": f"Would send to {number}: {message}"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

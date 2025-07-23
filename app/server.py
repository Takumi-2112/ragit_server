from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from rag_chain import chatbot_talk

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return "RAGIT Server is running!"

@app.route('/message', methods=['POST'])
def message():
    data = request.get_json()

    user_message = data.get('message', '')

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    # Send message to AI setup function
    ai_response = chatbot_talk(user_message)

    response = {
        "reply": "Message received!",
        "data": ai_response
    }
    return jsonify(response)

if __name__ == '__main__':
    # app.run() 
    app.run(debug=True, host='', port=5000)  # Run on all interfaces for local testing
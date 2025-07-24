from flask import Flask, request, jsonify
from flask_cors import CORS
from rag_chain import chatbot_talk

app = Flask(__name__)

# Configure CORS properly
CORS(
    app,
    resources={
        r"/message": {
            "origins": ["http://localhost:5173", "*"],
            "methods": ["POST"],
            "allow_headers": ["Content-Type"]
        }
    }
)

@app.route('/')
def home():
    return "RAGIT Server is running!"

@app.route('/message', methods=['POST', 'OPTIONS'])  # Added OPTIONS for preflight
def message():
    if request.method == 'OPTIONS':
        # Handle preflight request
        response = jsonify({"status": "preflight"})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response

    data = request.get_json()

    if not data or 'message' not in data:
        return jsonify({"error": "No message provided"}), 400

    user_message = data['message']

    # Send message to AI setup function
    ai_response = chatbot_talk(user_message)

    response = jsonify({
        "message": ai_response  # Changed from "data" to match your frontend expectation
    })
    
    # Add CORS headers to the actual response
    response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
    return response

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)  # Fixed host parameter
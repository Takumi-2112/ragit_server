from flask import Flask, request, jsonify
from flask_cors import CORS
from rag_chain import chatbot_talk, url_to_vectorstore
from pdf_converter import add_pdf_to_vectorstore
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from config import JWT_SECRET
from db.connection import get_db_connection, execute_query, close_connection  
from db.queries.users import (
    create_new_user_query,
    get_all_users_query,
    get_user_by_id_query,
    get_user_by_username_query,
    get_user_by_email_query,
    get_user_login_query,
    get_newest_user_query,
    update_user_email_query,
    update_user_password_query,
    update_user_email_and_password_query,
    delete_user_query
    
)
from db.queries.chats import (
    create_new_chat_message_query,
    get_all_chats_by_user_query,
    get_last_message_order_by_user_query,
    delete_all_chats_by_user_query
)

# JWT imports
import jwt
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)

# Configure CORS properly
CORS(
    app,
    resources={
        r"/*": {
            "origins": ["http://localhost:5173"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    }
)

# JWT Helper Functions
def generate_jwt_token(user_id, username):
    """Generate JWT token for authenticated user"""
    payload = {
        'user_id': user_id,
        'username': username,
        'exp': datetime.utcnow() + timedelta(hours=24)  # Token expires in 24 hours
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def verify_jwt_token(token):
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None  # Token expired
    except jwt.InvalidTokenError:
        return None  # Invalid token

def require_auth(f):
    """Decorator to require authentication for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Handle OPTIONS requests for CORS
        if request.method == 'OPTIONS':
            response = jsonify({"status": "preflight"})
            response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
            return response
        
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            error_response = jsonify({"error": "Authentication required"})
            error_response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
            return error_response, 401
        
        token = auth_header.split(' ')[1]
        payload = verify_jwt_token(token)
        
        if not payload:
            error_response = jsonify({"error": "Invalid or expired token"})
            error_response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
            return error_response, 401
        
        # Add user info to request context
        request.user_id = payload['user_id']
        request.username = payload['username']
        
        return f(*args, **kwargs)
    return decorated_function

def save_chat_message(user_id, message_text, sender):
    """Save a single chat message to the database"""
    try:
        # Get the last message order for this user
        last_order_query = get_last_message_order_by_user_query()
        result = execute_query(last_order_query, params=(user_id,), fetch_one=True)
        next_order = (result['last_order'] if result and result['last_order'] else 0) + 1
        
        # Save the message
        query = create_new_chat_message_query()
        execute_query(query, params=(user_id, message_text, sender, next_order))
        return True
    except Exception as e:
        # print(f"Error saving chat message: {str(e)}")
        return False

def get_user_chat_history(user_id):
    """Retrieve all chat messages for a user"""
    try:
        query = get_all_chats_by_user_query()
        messages = execute_query(query, params=(user_id,), fetch_all=True)
        
        # Convert to the format expected by the frontend
        chat_history = []
        if messages:
            for msg in messages:
                chat_history.append({
                    "sender": msg['sender'],
                    "text": msg['message_text']
                })
        
        return chat_history
    except Exception as e:
        # print(f"Error retrieving chat history: {str(e)}")
        return []

@app.route('/')
def home():
    return "RAGIT Server is running!"
  
@app.route('/register', methods=['POST', 'OPTIONS'])
def register_user():
    if request.method == 'OPTIONS':
        response = jsonify({"status": "preflight"})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response

    try:
        data = request.get_json()
        
        if not data or 'username' not in data or 'email' not in data or 'password' not in data:
            return jsonify({"error": "Missing required fields"}), 400

        username = data['username'].strip()
        email = data['email'].strip().lower()
        password = data['password']

        # Basic validation
        if len(username) < 3:
            return jsonify({"error": "Username must be at least 3 characters long"}), 400
        
        if len(password) < 6:
            return jsonify({"error": "Password must be at least 6 characters long"}), 400

        # Check if user/email exists
        existing_user = execute_query(get_user_by_username_query(), params=(username,), fetch_one=True)
        if existing_user:
            return jsonify({"error": "Username already exists"}), 409

        existing_email = execute_query(get_user_by_email_query(), params=(email,), fetch_one=True)
        if existing_email:
            return jsonify({"error": "Email already exists"}), 409

        # Hash password - this is the key security step
        password_hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)

        # Create user with hashed password (never store plain text password)
        result = execute_query(create_new_user_query(), params=(username, email, password_hash, "temp_path"), fetch_one=True)
        user_id = result['id']

        # Update vectorstore path
        actual_vectorstore_path = f"db/vectorstores/user_{user_id}_vectorstore"
        os.makedirs(actual_vectorstore_path, exist_ok=True)
        execute_query("UPDATE users SET vectorstore_path=%s WHERE id=%s", params=(actual_vectorstore_path, user_id))

        # Initial chat message
        save_chat_message(user_id, "Hello! How can I assist you today?", "bot")

        # Generate JWT token
        token = generate_jwt_token(user_id, username)

        response = jsonify({
            "message": "User registered successfully", 
            "token": token, 
            "user_id": user_id, 
            "username": username
        })
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        return response, 201

    except Exception as e:
        print(f"Registration error: {e}")  # Enable for debugging
        error_response = jsonify({"error": "Registration failed"})
        error_response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        return error_response, 500

@app.route('/login', methods=['POST', 'OPTIONS'])
def login_user():
    if request.method == 'OPTIONS':
        response = jsonify({"status": "preflight"})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response

    try:
        data = request.get_json()
        
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({"error": "Missing required fields"}), 400

        username = data['username'].strip()
        password = data['password']  # Plain text password from frontend

        # Get user data including password hash
        user = execute_query(get_user_login_query(), params=(username,), fetch_one=True)
        
        # Check if user exists and password is correct
        # check_password_hash compares plain text password with stored hash
        if not user or not check_password_hash(user['password_hash'], password):
            return jsonify({"error": "Invalid username or password"}), 401

        # Generate JWT token for successful login
        token = generate_jwt_token(user['id'], user['username'])
        
        # Get user's chat history
        chat_history = get_user_chat_history(user['id'])

        response = jsonify({
            "message": "Login successful", 
            "token": token, 
            "user_id": user['id'], 
            "username": user['username'], 
            "chat_history": chat_history
        })
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        return response, 200

    except Exception as e:
        print(f"Login error: {e}")  # Enable for debugging
        error_response = jsonify({"error": "Login failed"})
        error_response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        return error_response, 500


@app.route('/chat-history', methods=['GET', 'OPTIONS'])
@require_auth
def get_chat_history():
    if request.method == 'OPTIONS':
        response = jsonify({"status": "preflight"})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        return response
    
    try:
        user_id = request.user_id
        chat_history = get_user_chat_history(user_id)
        
        response = jsonify({
            "chat_history": chat_history,
            "status": "success"
        })
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        return response, 200
        
    except Exception as e:
        # print(f"Error retrieving chat history: {str(e)}")
        error_response = jsonify({"error": "Failed to retrieve chat history"})
        error_response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        return error_response, 500

@app.route('/clear-chat', methods=['POST', 'OPTIONS'])
@require_auth
def clear_chat():
    if request.method == 'OPTIONS':
        response = jsonify({"status": "preflight"})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    try:
        user_id = request.user_id
        
        # Clear all chat messages for this user
        query = delete_all_chats_by_user_query()
        execute_query(query, params=(user_id,))
        
        # Add initial bot message
        save_chat_message(user_id, "Hello! How can I assist you today?", "bot")
        
        response = jsonify({
            "message": "Chat history cleared successfully",
            "status": "success"
        })
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        return response, 200
        
    except Exception as e:
        # print(f"Error clearing chat history: {str(e)}")
        error_response = jsonify({"error": "Failed to clear chat history"})
        error_response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        return error_response, 500

@app.route('/upload-pdf', methods=['POST', 'OPTIONS'])
@require_auth
def upload_pdf():
    try:
        # Check if file is in the request
        if 'file' not in request.files:
            error_response = jsonify({'error': 'No file provided'})
            error_response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
            return error_response, 400
        
        file = request.files['file']
        
        # Check if file was actually selected
        if file.filename == '':
            error_response = jsonify({'error': 'No file selected'})
            error_response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
            return error_response, 400
        
        # Check if it's a PDF file
        if not file.filename.lower().endswith('.pdf'):
            error_response = jsonify({'error': 'File must be a PDF'})
            error_response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
            return error_response, 400
        
        # Create pdf folder if it doesn't exist
        current_dir = os.path.dirname(os.path.abspath(__file__))
        pdf_folder = os.path.join(current_dir, "pdf")
        os.makedirs(pdf_folder, exist_ok=True)
        
        # Secure the filename
        filename = secure_filename(file.filename)
        file_path = os.path.join(pdf_folder, filename)
        
        # Save the file
        file.save(file_path)
        # print(f"PDF saved to: {file_path}")
        
        # Use user_id from JWT token
        user_id = request.user_id
        success = add_pdf_to_vectorstore(file_path, filename, user_id)
        
        if success:
            response = jsonify({
                'message': 'PDF uploaded and processed successfully',
                'filename': filename,
                'status': 'success'
            })
        else:
            response = jsonify({
                'message': 'PDF uploaded but processing failed',
                'filename': filename,
                'status': 'partial_success'
            })
        
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        return response, 200
        
    except Exception as e:
        # print(f"Upload error: {str(e)}")
        error_response = jsonify({'error': f'Upload failed: {str(e)}'})
        error_response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        return error_response, 500

@app.route('/ingest-url', methods=['POST', 'OPTIONS'])
@require_auth
def ingest_url():
    try:
        data = request.get_json()
        
        url = data.get('url')
        
        if not url:
            error_response = jsonify({'error': 'URL is required'})
            error_response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
            return error_response, 400
        
        # Basic URL validation
        if not url.startswith(('http://', 'https://')):
            error_response = jsonify({'error': 'Invalid URL format. Must start with http:// or https://'})
            error_response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
            return error_response, 400
        
        # Use user_id from JWT token
        user_id = request.user_id
        success = url_to_vectorstore(url, user_id)
        
        if success:
            response = jsonify({
                'message': 'URL content successfully ingested and added to vectorstore',
                'url': url
            })
        else:
            response = jsonify({
                'message': 'Failed to process URL content',
                'url': url
            })
        
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        return response, 200
        
    except Exception as e:
        # print(f"Error processing URL: {str(e)}")
        error_response = jsonify({'error': f'Failed to process URL: {str(e)}'})
        error_response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        return error_response, 500

@app.route('/message', methods=['POST', 'OPTIONS'])
@require_auth
def message():
    data = request.get_json()

    if not data or 'message' not in data:
        error_response = jsonify({"error": "No message provided"})
        error_response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        return error_response, 400

    user_message = data['message']
    user_id = request.user_id

    # Save user message to database
    save_chat_message(user_id, user_message, "user")

    # Send message to AI setup function with user_id
    ai_response = chatbot_talk(user_message, user_id)

    # Save AI response to database
    save_chat_message(user_id, ai_response, "bot")

    response = jsonify({
        "message": ai_response
    })
    
    response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
    return response

# Logout endpoint
@app.route('/logout', methods=['POST', 'OPTIONS'])
@require_auth
def logout():
    if request.method == 'OPTIONS':
        response = jsonify({"status": "preflight"})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    try:
        # Since JWT is stateless, we mainly just confirm the logout
        # In the future, you could add token blacklisting here if needed
        username = request.username
        
        response = jsonify({
            "message": f"User {username} logged out successfully",
            "status": "success"
        })
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        return response, 200
        
    except Exception as e:
        # print(f"Error during logout: {str(e)}")
        error_response = jsonify({"error": "Logout failed due to server error"})
        error_response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        return error_response, 500

# Optional: Add token refresh endpoint
@app.route('/refresh-token', methods=['POST', 'OPTIONS'])
@require_auth
def refresh_token():
    if request.method == 'OPTIONS':
        response = jsonify({"status": "preflight"})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    try:
        # Generate new token with extended expiration
        new_token = generate_jwt_token(request.user_id, request.username)
        
        response = jsonify({
            "message": "Token refreshed successfully",
            "token": new_token
        })
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        return response, 200
        
    except Exception as e:
        # print(f"Error refreshing token: {str(e)}")
        error_response = jsonify({"error": "Token refresh failed"})
        error_response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        return error_response, 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8123)
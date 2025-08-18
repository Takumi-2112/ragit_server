from flask import Flask, request, jsonify
from flask_cors import CORS
from rag_chain import chatbot_talk, url_to_vectorstore
from pdf_converter import add_pdf_to_vectorstore
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from app.db.connection import get_db_connection, execute_query, close_connection  
from db.queries.users import (
    create_new_user_query,
    get_all_users_query,
    get_user_by_id_query,
    get_user_by_username_query,
    get_user_by_email_query,
    get_newest_user_query,
    update_user_email_query,
    update_user_password_query,
    update_user_email_and_password_query,
    delete_user_query
)

# JWT imports
import jwt
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)

# JWT Configuration (use environment variable in production)
JWT_SECRET = "your-secret-key-here"  # Move to config.py or .env in production

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

@app.route('/')
def home():
    return "RAGIT Server is running!"
  
@app.route('/register', methods=['POST', 'OPTIONS'])
def register_user():
    # Handle preflight requests
    if request.method == 'OPTIONS':
        response = jsonify({"status": "preflight"})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    try:
        data = request.get_json()
        
        if not data or 'username' not in data or 'email' not in data or 'password' not in data:
            error_response = jsonify({"error": "Missing required fields: username, email, password"})
            error_response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
            return error_response, 400
        
        username = data['username'].strip()
        email = data['email'].strip().lower()
        password = data['password']
        
        # Check if username already exists
        existing_username_query = get_user_by_username_query()
        existing_user = execute_query(existing_username_query, params=(username,), fetch_one=True)
        if existing_user:
            error_response = jsonify({"error": "Username already exists"})
            error_response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
            return error_response, 409
        
        # Check if email already exists
        existing_email_query = get_user_by_email_query()
        existing_email = execute_query(existing_email_query, params=(email,), fetch_one=True)
        if existing_email:
            error_response = jsonify({"error": "Email already exists"})
            error_response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
            return error_response, 409
        
        # Hash the password
        password_hash = generate_password_hash(password)
        
        # Create vectorstore path for the new user
        temp_vectorstore_path = f"db/vectorstores/temp_user_vectorstore"
        
        # Create new user in the database
        query = create_new_user_query()
        result = execute_query(query, params=(username, email, password_hash, temp_vectorstore_path), fetch_one=True)
        
        if result and 'id' in result:
            user_id = result['id']
            
            # Update vectorstore path with actual user ID
            actual_vectorstore_path = f"db/vectorstores/user_{user_id}_vectorstore"
            
            # Create the vectorstore directory
            current_dir = os.path.dirname(os.path.abspath(__file__))
            vectorstore_full_path = os.path.join(current_dir, actual_vectorstore_path)
            os.makedirs(vectorstore_full_path, exist_ok=True)
            
            # Update user record with correct vectorstore path
            update_query = """
            UPDATE users SET vectorstore_path = %s WHERE id = %s
            """
            execute_query(update_query, params=(actual_vectorstore_path, user_id))
            
            # Generate JWT token for immediate login
            token = generate_jwt_token(user_id, username)
            
            success_response = jsonify({
                "message": "User registered successfully",
                "token": token,
                "user_id": user_id,
                "username": username
            })
            success_response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
            return success_response, 201
        else:
            error_response = jsonify({"error": "Failed to create user"})
            error_response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
            return error_response, 500
            
    except Exception as e:
        print(f"Error registering user: {str(e)}")
        error_response = jsonify({"error": "Registration failed due to server error"})
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
            error_response = jsonify({"error": "Missing required fields: username, password"})
            error_response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
            return error_response, 400
        
        username = data['username'].strip()
        password = data['password']
        
        # Fetch user by username
        user_query = get_user_by_username_query()
        user = execute_query(user_query, params=(username,), fetch_one=True)
        
        if not user:
            error_response = jsonify({"error": "Invalid username or password"})
            error_response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
            return error_response, 401
        
        # Verify password
        if not check_password_hash(user['password_hash'], password):
            error_response = jsonify({"error": "Invalid username or password"})
            error_response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
            return error_response, 401
        
        # Generate JWT token
        token = generate_jwt_token(user['id'], user['username'])
        
        # Successful login
        success_response = jsonify({
            "message": "Login successful",
            "token": token,
            "user_id": user['id'],
            "username": user['username']
        })
        success_response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        return success_response, 200
        
    except Exception as e:
        print(f"Error during login: {str(e)}")
        error_response = jsonify({"error": "Login failed due to server error"})
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
        print(f"PDF saved to: {file_path}")
        
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
        print(f"Upload error: {str(e)}")
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
        print(f"Error processing URL: {str(e)}")
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
    # Use user_id from JWT token instead of request body
    user_id = request.user_id

    # Send message to AI setup function with user_id
    ai_response = chatbot_talk(user_message, user_id)

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
        print(f"Error during logout: {str(e)}")
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
        print(f"Error refreshing token: {str(e)}")
        error_response = jsonify({"error": "Token refresh failed"})
        error_response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        return error_response, 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8123)
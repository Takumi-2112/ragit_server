from flask import Flask, request, jsonify
from flask_cors import CORS
from rag_chain import chatbot_talk, url_to_vectorstore
from pdf_converter import add_pdf_to_vectorstore
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from db.conection import get_db_connection, execute_query, close_connection  
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

app = Flask(__name__)

# Configure CORS properly
CORS(
    app,
    resources={
        r"/message": {
            "origins": ["http://localhost:5173"],
            "methods": ["POST"],
            "allow_headers": ["Content-Type"]
        }
    }
)

@app.route('/')
def home():
    return "RAGIT Server is running!"
  
@app.route('/register', methods=['POST', 'OPTIONS'])
def register_user():
  # this ensures that the server can handle preflight requests
  # which are sent by the browser before the actual POST request
  # to check if the server accepts the request 
    if request.method == 'OPTIONS':
        response = jsonify({"status": "preflight"})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    try:
        # Get JSON data from the request
        # This is where the frontend sends the user registration data
        # e.g. { "username": "testuser", "email": "test@example.com", "password": "securepassword" }
        data = request.get_json()
        
        # if data is None or missing required fields, return an error response
        # this is to ensure that the request contains the necessary information
        if not data or 'username' not in data or 'email' not in data or 'password' not in data:
            error_response = jsonify({"error": "Missing required fields: username, email, password"})
            error_response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
            return error_response, 400
        
        # Extract and sanitize user input
        # This is to prevent SQL injection and ensure that the data is clean
        username = data['username'].strip()
        email = data['email'].strip().lower()
        password = data['password']
        
        # Basic validation
        # Uncomment these lines if you want to enforce minimum length for username and password
        # if len(username) < 3:
        #     error_response = jsonify({"error": "Username must be at least 3 characters long"})
        #     error_response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        #     return error_response, 400
            
        # if len(password) < 6:
        #     error_response = jsonify({"error": "Password must be at least 6 characters long"})
        #     error_response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        #     return error_response, 400
        
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
        # We'll use a temporary ID pattern, then update after user creation
        # its temporary because we don't have the user ID yet
        temp_vectorstore_path = f"db/vectorstores/temp_user_vectorstore"
        
        # Create new user in the database
        query = create_new_user_query()
        result = execute_query(query, params=(username, email, password_hash, temp_vectorstore_path), fetch_one=True)
        
        # If user creation was successful, result should contain the new user's ID
        if result and 'id' in result:
            user_id = result['id']
            
            # Update vectorstore path with actual user ID once we have it
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
            
            success_response = jsonify({
                "message": "User registered successfully",
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
        from werkzeug.security import check_password_hash
        if not check_password_hash(user['password_hash'], password):
            error_response = jsonify({"error": "Invalid username or password"})
            error_response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
            return error_response, 401
        
        # Successful login
        success_response = jsonify({
            "message": "Login successful",
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
def upload_pdf():
    if request.method == 'OPTIONS':
        response = jsonify({"status": "preflight"})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    try:
        # Check if file is in the request
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        # Get user_id from form data or JSON
        user_id = request.form.get('user_id')
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        file = request.files['file']
        
        # Check if file was actually selected
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Check if it's a PDF file
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'File must be a PDF'}), 400
        
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
        
        # Process the PDF and add to user's vectorstore
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
        
        # Add CORS headers
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        return response, 200
        
    except Exception as e:
        print(f"Upload error: {str(e)}")
        error_response = jsonify({'error': f'Upload failed: {str(e)}'})
        error_response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        return error_response, 500


@app.route('/ingest-url', methods=['POST', 'OPTIONS'])
def ingest_url():
    if request.method == 'OPTIONS':
        response = jsonify({"status": "preflight"})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    try:
        # Get the JSON data from the request
        data = request.get_json()
        
        # Extract the URL and user_id from the request data
        url = data.get('url')
        user_id = data.get('user_id')
        
        # Validate that both URL and user_id were provided
        if not url:
            error_response = jsonify({'error': 'URL is required'})
            error_response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
            return error_response, 400
            
        if not user_id:
            error_response = jsonify({'error': 'User ID is required'})
            error_response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
            return error_response, 400
        
        # Basic URL validation
        if not url.startswith(('http://', 'https://')):
            error_response = jsonify({'error': 'Invalid URL format. Must start with http:// or https://'})
            error_response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
            return error_response, 400
        
        # Process the URL and add to user's vectorstore
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
def message():
    if request.method == 'OPTIONS':
        response = jsonify({"status": "preflight"})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response

    data = request.get_json()

    if not data or 'message' not in data:
        return jsonify({"error": "No message provided"}), 400
    
    if 'user_id' not in data:
        return jsonify({"error": "User ID is required"}), 400

    user_message = data['message']
    user_id = data['user_id']

    # Send message to AI setup function with user_id
    ai_response = chatbot_talk(user_message, user_id)

    response = jsonify({
        "message": ai_response
    })
    
    # Add CORS headers to the actual response
    response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
    return response
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)  # Fixed host parameter
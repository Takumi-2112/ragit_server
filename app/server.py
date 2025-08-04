from flask import Flask, request, jsonify
from flask_cors import CORS
from rag_chain import chatbot_talk, url_to_vectorstore
from pdf_converter import add_pdf_to_vectorstore
import os
from werkzeug.utils import secure_filename

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
        
        # Process the PDF and add to vectorstore
        success = add_pdf_to_vectorstore(file_path, filename)
        
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
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        response = jsonify({"status": "preflight"})
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    try:
        # Get the JSON data from the request
        data = request.get_json()
        
        # Extract the URL from the request data
        url = data.get('url')
        
        # Validate that URL was provided
        if not url:
            error_response = jsonify({'error': 'URL is required'})
            error_response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
            return error_response, 400
        
        # Basic URL validation (optional but recommended)
        if not url.startswith(('http://', 'https://')):
            error_response = jsonify({'error': 'Invalid URL format. Must start with http:// or https://'})
            error_response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
            return error_response, 400
        
        # Process the URL and add to vectorstore
        url_to_vectorstore(url)
        
        # Return success response with CORS headers
        response = jsonify({
            'message': 'URL content successfully ingested and added to vectorstore',
            'url': url
        })
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        return response, 200
        
    except Exception as e:
        print(f"Error processing URL: {str(e)}")
        error_response = jsonify({'error': f'Failed to process URL: {str(e)}'})
        error_response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
        return error_response, 500
   


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
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import shutil
import uuid
from datetime import datetime
from rag_chain import (
    embeddings,
    vectorstore,
    retriever,
    model,
    rag_chain,
    HumanMessage,
    SystemMessage
)

# Initialize FastAPI app
app = FastAPI(
    title="RAG Chatbot API",
    description="API for PDF-based RAG Chatbot",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models
class ChatRequest(BaseModel):
    message: str
    chat_history: Optional[List[dict]] = None

class ChatResponse(BaseModel):
    response: str
    chat_history: List[dict]

class UploadResponse(BaseModel):
    message: str
    filename: str
    file_type: str
    success: bool

class HealthCheckResponse(BaseModel):
    status: str
    timestamp: str

# Utility functions
def convert_chat_history(chat_history: Optional[List[dict]]) -> List:
    """
    Convert chat history from frontend format to LangChain message format
    """
    if not chat_history:
        return []
    
    converted = []
    for msg in chat_history:
        if msg["role"] == "user":
            converted.append(HumanMessage(content=msg["content"]))
        else:
            converted.append(SystemMessage(content=msg["content"]))
    return converted

def process_uploaded_file(file: UploadFile, destination_folder: str):
    """
    Save uploaded file to specified folder
    """
    try:
        os.makedirs(destination_folder, exist_ok=True)
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(destination_folder, unique_filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return unique_filename, file_path
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

# API endpoints
@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    Health check endpoint
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Handle chat messages with RAG functionality
    """
    try:
        # Convert chat history to LangChain format
        lc_chat_history = convert_chat_history(request.chat_history)
        
        # Process the query
        result = rag_chain.invoke({
            "input": request.message,
            "chat_history": lc_chat_history
        })
        
        # Clean up the response
        clean_response = result["answer"].replace("▪", "•")
        
        # Update chat history
        updated_history = request.chat_history or []
        updated_history.extend([
            {"role": "user", "content": request.message},
            {"role": "assistant", "content": clean_response}
        ])
        
        return {
            "response": clean_response,
            "chat_history": updated_history
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing chat request: {str(e)}"
        )

@app.post("/upload-pdf", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload and process a PDF file
    """
    try:
        # Save the PDF
        pdf_filename, pdf_path = process_uploaded_file(file, "pdf")
        
        # Convert to markdown (you'll need to import your pdf_converter functions)
        from pdf_converter import convert_PDF_to_markdown
        markdown_content = convert_PDF_to_markdown(pdf_path)
        
        # Save markdown
        md_filename = pdf_filename.replace(".pdf", ".md")
        md_path = os.path.join("markdown", md_filename)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        
        # Re-index the vectorstore (you might want to make this more efficient)
        # For now, we'll just indicate success but not automatically re-index
        # In production, you might want to implement a background task for this
        
        return {
            "message": "File uploaded and converted successfully. Re-indexing needed.",
            "filename": pdf_filename,
            "file_type": "pdf",
            "success": True
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing PDF: {str(e)}"
        )

@app.post("/reindex")
async def reindex_vectorstore():
    """
    Reindex the vectorstore with all current markdown files
    """
    try:
        # This would need to implement the vectorstore creation logic from rag_chain.py
        # For now, we'll just return a message indicating this endpoint needs implementation
        return {"message": "Reindex endpoint needs implementation"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reindexing: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
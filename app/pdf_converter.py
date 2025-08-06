from rag_chain import get_user_vectorstore
import fitz  # PyMuPDF
import os
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

def convert_PDF_to_markdown(pdf_document_path):
    """Convert a single PDF to markdown content"""
    pdf_document = fitz.open(pdf_document_path)
    markdown_content = ""
    
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        text = page.get_text("text")
        
        # Preserve basic formatting
        text = text.replace("\n", "  \n")
        text = text.replace("•", "-")
        
        markdown_content += f"## Page {page_num + 1}\n\n{text}\n\n"
    
    pdf_document.close()
    return markdown_content

def process_pdf_content(pdf_path, filename):
    """Convert PDF to documents for vectorstore processing"""
    try:
        # Convert PDF to markdown
        markdown_content = convert_PDF_to_markdown(pdf_path)
        
        if not markdown_content.strip():
            print(f"No content extracted from {filename}")
            return None
        
        # Create document
        document = Document(
            page_content=markdown_content,
            metadata={"source": filename, "type": "pdf"}
        )
        
        # Split the document into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n## ", "\n##", "\n#", "\n\n", "\n", "  ", " ", ""]
        )
        
        split_docs = text_splitter.split_documents([document])
        
        print(f"Successfully processed {filename} into {len(split_docs)} chunks")
        return split_docs
        
    except Exception as e:
        print(f"Error processing PDF {filename}: {str(e)}")
        return None

def add_pdf_to_vectorstore(pdf_path, filename, user_id):
    """Convert PDF and add to user-specific vectorstore"""
    try:
        # Process the PDF content
        split_docs = process_pdf_content(pdf_path, filename)
        
        if not split_docs:
            return False
        
        # Get user's vectorstore
        vectorstore = get_user_vectorstore(user_id)
        
        # Add to user's vectorstore
        vectorstore.add_documents(split_docs)
        
        # Save markdown file to user-specific folder (optional)
        markdown_content = convert_PDF_to_markdown(pdf_path)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        user_markdown_folder = os.path.join(current_dir, "markdown", f"user_{user_id}")
        os.makedirs(user_markdown_folder, exist_ok=True)
        
        md_filename = filename.replace(".pdf", ".md")
        md_path = os.path.join(user_markdown_folder, md_filename)
        
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        
        print(f"Successfully added {filename} to user {user_id}'s vectorstore")
        return True
        
    except Exception as e:
        print(f"Error processing PDF {filename} for user {user_id}: {str(e)}")
        return False

# Keep old function for any existing code that might use it (with default user)
def add_pdf_to_vectorstore_legacy(pdf_path, filename):
    """Legacy function - uses default user"""
    return add_pdf_to_vectorstore(pdf_path, filename, "default")
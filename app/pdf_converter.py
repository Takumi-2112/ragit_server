from rag_chain import vectorstore
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

def add_pdf_to_vectorstore(pdf_path, filename):
    """Convert PDF to markdown and add to vectorstore"""
    try:
        # Convert PDF to markdown
        markdown_content = convert_PDF_to_markdown(pdf_path)
        
        # Save markdown file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        markdown_folder = os.path.join(current_dir, "markdown")
        os.makedirs(markdown_folder, exist_ok=True)
        
        md_filename = filename.replace(".pdf", ".md")
        md_path = os.path.join(markdown_folder, md_filename)
        
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        
        print(f"Converted {filename} to {md_filename}")
        
        # Add to vectorstore
        document = Document(
            page_content=markdown_content,
            metadata={"source": filename}
        )
        
        # Split the document into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n## ", "\n##", "\n#", "\n\n", "\n", "  ", " ", ""]
        )
        
        split_docs = text_splitter.split_documents([document])
        
        # Add to vectorstore
        vectorstore.add_documents(split_docs)
        vectorstore.persist()
        
        print(f"Successfully added {filename} to vectorstore")
        return True
        
    except Exception as e:
        print(f"Error processing PDF {filename}: {str(e)}")
        return False
# pdf_converter.py (updated)
import fitz  # PyMuPDF

def convert_PDF_to_markdown(pdf_path: str) -> str:
    """Convert a single PDF file to markdown"""
    pdf_document = fitz.open(pdf_path)
    markdown_content = ""
    
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        text = page.get_text("text")
        
        # Preserve basic formatting
        text = text.replace("\n", "  \n")
        text = text.replace("•", "-")
        
        markdown_content += f"## Page {page_num + 1}\n\n{text}\n\n"
    
    return markdown_content
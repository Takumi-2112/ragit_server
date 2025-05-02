import fitz  # PyMuPDF
# from azure.storage.filedatalake import DataLakeServiceClient
import io
import os
 
 current_dir = os.path.dirname(os.path.abspath(__file__))
 
 def convert_PDF_to_markdown(pdf_document_path):
     pdf_document = fitz.open(pdf_document_path)
     markdown_content = ""
     
     for page_num in range(len(pdf_document)):
         page = pdf_document.load_page(page_num)
         text = page.get_text()
         
         # Clean up the text
         text = text.replace("•", "▪")  # Standardize bullet points
         text = text.replace("\n", " ").strip()  # Remove excessive newlines
         text = " ".join(text.split())  # Remove extra whitespace
         
         markdown_content += f"## Page {page_num + 1}\n\n{text}\n\n"
     
     return markdown_content
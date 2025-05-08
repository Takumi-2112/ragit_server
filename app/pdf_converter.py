import fitz  # PyMuPDF
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
pdf_folder = os.path.join(current_dir, "pdf")  # Folder containing PDFs
output_folder = os.path.join(current_dir, "markdown")  # Folder to save markdown files

os.makedirs(output_folder, exist_ok=True)

def convert_PDF_to_markdown(pdf_document_path):
    pdf_document = fitz.open(pdf_document_path)
    markdown_content = ""
    
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        text = page.get_text("text")  # Use "text" instead of default get_text()
        
        # Preserve basic formatting
        text = text.replace("\n", "  \n")  # Markdown line breaks need two spaces
        text = text.replace("•", "-")      # Standard markdown bullets
        
        markdown_content += f"## Page {page_num + 1}\n\n{text}\n\n"
    
    return markdown_content

# Loop through all PDFs in the folder
for filename in os.listdir(pdf_folder):
    if filename.endswith(".pdf"):
        pdf_path = os.path.join(pdf_folder, filename)
        markdown = convert_PDF_to_markdown(pdf_path)

        md_filename = filename.replace(".pdf", ".md")
        output_path = os.path.join(output_folder, md_filename)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown)

        print(f"Converted {filename} to {md_filename}")

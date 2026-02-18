import os
import fitz # PyMuPDF
from docx import Document

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extracts text from a PDF file."""
    text = ""
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            text += page.get_text()
        doc.close()
    except Exception as e:
        print(f"Error extracting text from PDF {pdf_path}: {e}")
        # In a real scenario, you might want to log this error and/or return a specific error message
        return f"Error: Could not extract text from PDF ({e})"
    return text

def extract_text_from_docx(docx_path: str) -> str:
    """Extracts text from a DOCX file."""
    text = ""
    try:
        doc = Document(docx_path)
        for para in doc.paragraphs:
            text += para.text + "\n" # Corrected line: added missing closing quote and newline
    except Exception as e:
        print(f"Error extracting text from DOCX {docx_path}: {e}")
        return f"Error: Could not extract text from DOCX ({e})"
    return text

def extract_text(file_path: str) -> str:
    """
    Extracts text from a given file based on its extension.
    Supports PDF and DOCX.
    """
    if not os.path.exists(file_path):
        return "Error: File not found."

    file_extension = os.path.splitext(file_path)[1].lower()

    if file_extension == ".pdf":
        return extract_text_from_pdf(file_path)
    elif file_extension == ".docx":
        return extract_text_from_docx(file_path)
    else:
        return "Error: Unsupported file type for text extraction."

# Example usage (for testing)
if __name__ == "__main__":
    # Create dummy files for testing
    dummy_pdf_path = "dummy.pdf"
    dummy_docx_path = "dummy.docx"

    # Create dummy PDF
    try:
        # These imports are only for the example usage and might not be available
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter

        c = canvas.Canvas(dummy_pdf_path, pagesize=letter)
        c.drawString(100, 750, "Hello, this is a dummy PDF file.")
        c.drawString(100, 730, "It contains some sample text for testing.")
        c.save()
    except ImportError:
        print("reportlab not installed. Cannot create dummy PDF.")
        print("Skipping dummy PDF creation and extraction test.")
        dummy_pdf_path = None
    
    # Create dummy DOCX
    try:
        from docx import Document as DocxDocument
        doc = DocxDocument()
        doc.add_paragraph("This is a dummy DOCX file.")
        doc.add_paragraph("It contains some sample text for testing the extractor.")
        doc.save(dummy_docx_path)
    except ImportError:
        print("python-docx not installed. Cannot create dummy DOCX.")
        print("Skipping dummy DOCX creation and extraction test.")
        dummy_docx_path = None

    if dummy_pdf_path and os.path.exists(dummy_pdf_path):
        print(f"\n--- Text from {dummy_pdf_path} ---")
        pdf_text = extract_text(dummy_pdf_path)
        print(pdf_text)
        os.remove(dummy_pdf_path)

    if dummy_docx_path and os.path.exists(dummy_docx_path):
        print(f"\n--- Text from {dummy_docx_path} ---")
        docx_text = extract_text(dummy_docx_path)
        print(docx_text)
        os.remove(dummy_docx_path)

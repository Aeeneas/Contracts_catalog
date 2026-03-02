import os
import fitz # PyMuPDF
from docx import Document
import pandas as pd
import win32com.client as win32
import pythoncom
import base64
import requests
from io import BytesIO
try:
    from config import settings
except ImportError:
    from .config import settings

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extracts text from a PDF file. If it's a scan, uses OpenAI Vision OCR."""
    text = ""
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            text += page.get_text()
        
        # If very little text is extracted, it's likely a scan
        if len(text.strip()) < 300 and len(doc) > 0:
            print(f"PDF {pdf_path} seems to be a scan. Using OpenAI Vision OCR...")
            return extract_text_via_openai_vision(doc)
            
        doc.close()
    except Exception as e:
        print(f"Error extracting text from PDF {pdf_path}: {e}")
        return f"Error: Could not extract text from PDF ({e})"
    return text

def extract_text_via_openai_vision(doc: fitz.Document) -> str:
    """Converts key PDF pages to images and sends them to OpenAI for OCR."""
    if not settings.OPENAI_API_KEY:
        return "Error: OpenAI API Key not configured for OCR."

    # Identify key pages: first 5 and last 5 (where most metadata resides)
    total_pages = len(doc)
    pages_to_ocr = list(range(min(5, total_pages)))
    if total_pages > 5:
        last_pages = list(range(max(5, total_pages - 5), total_pages))
        pages_to_ocr.extend([p for p in last_pages if p not in pages_to_ocr])

    combined_ocr_text = ""
    
    for page_num in pages_to_ocr:
        page = doc.load_page(page_num)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # Increase resolution for better OCR
        img_data = pix.tobytes("png")
        base64_image = base64.b64encode(img_data).decode('utf-8')

        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}"
            }
            payload = {
                "model": "gpt-4o-mini", # Using mini for cost-effective OCR, upgrade to gpt-4o if needed
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "This is a page from a contract. Please transcribe all the text you see on this page exactly as it is. Output ONLY the transcribed text."},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{base64_image}"}
                            }
                        ]
                    }
                ],
                "max_tokens": 2000
            }
            response = requests.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            page_text = response.json()['choices'][0]['message']['content']
            combined_ocr_text += f"\n--- PAGE {page_num + 1} (OCR) ---\n{page_text}\n"
        except Exception as e:
            print(f"Error during OpenAI OCR for page {page_num}: {e}")
            combined_ocr_text += f"\n[OCR Error on page {page_num + 1}]\n"

    doc.close()
    return combined_ocr_text

def extract_text_from_docx(docx_path: str) -> str:
    """Extracts text from a DOCX file."""
    text = ""
    try:
        doc = Document(docx_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        print(f"Error extracting text from DOCX {docx_path}: {e}")
        return f"Error: Could not extract text from DOCX ({e})"
    return text

def extract_text_from_doc(doc_path: str) -> str:
    """Extracts text from a legacy .doc file using win32com (requires MS Word)."""
    text = ""
    word = None
    try:
        pythoncom.CoInitialize()
        word = win32.Dispatch("Word.Application")
        word.Visible = False
        abs_path = os.path.abspath(doc_path)
        doc = word.Documents.Open(abs_path)
        text = doc.Content.Text
        doc.Close()
    except Exception as e:
        print(f"Error extracting text from DOC {doc_path}: {e}")
        return f"Error: Could not extract text from DOC ({e})"
    finally:
        if word:
            word.Quit()
        pythoncom.CoUninitialize()
    return text

def extract_text_from_xlsx(xlsx_path: str) -> str:
    """Extracts text from an XLSX file (all sheets)."""
    text = ""
    try:
        excel_data = pd.read_excel(xlsx_path, sheet_name=None, engine='openpyxl')
        for sheet_name, df in excel_data.items():
            text += f"Sheet: {sheet_name}\n"
            text += df.to_string(index=False) + "\n\n"
    except Exception as e:
        print(f"Error extracting text from XLSX {xlsx_path}: {e}")
        return f"Error: Could not extract text from XLSX ({e})"
    return text

def extract_text_from_xls(xls_path: str) -> str:
    """Extracts text from a legacy .xls file (all sheets)."""
    text = ""
    try:
        excel_data = pd.read_excel(xls_path, sheet_name=None, engine='xlrd')
        for sheet_name, df in excel_data.items():
            text += f"Sheet: {sheet_name}\n"
            text += df.to_string(index=False) + "\n\n"
    except Exception as e:
        print(f"Error extracting text from XLS {xls_path}: {e}")
        return f"Error: Could not extract text from XLS ({e})"
    return text

def extract_text(file_path: str) -> str:
    """
    Extracts text from a given file based on its extension.
    Supports PDF, DOCX, DOC, XLSX, XLS.
    Automatically detects scans and uses OpenAI OCR for PDFs.
    """
    if not os.path.exists(file_path):
        return "Error: File not found."

    file_extension = os.path.splitext(file_path)[1].lower()

    if file_extension == ".pdf":
        return extract_text_from_pdf(file_path)
    elif file_extension == ".docx":
        return extract_text_from_docx(file_path)
    elif file_extension == ".doc":
        return extract_text_from_doc(file_path)
    elif file_extension == ".xlsx":
        return extract_text_from_xlsx(file_path)
    elif file_extension == ".xls":
        return extract_text_from_xls(file_path)
    else:
        return "Error: Unsupported file type for text extraction."

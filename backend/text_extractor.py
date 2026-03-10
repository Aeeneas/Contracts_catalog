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

from ai_service import _get_session

def extract_text_from_pdf(pdf_path: str) -> str:
    """Извлекает текст из PDF. Использует гибридный подход: текст + Vision OCR для сканированных страниц."""
    full_text = ""
    try:
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        
        scanned_page_indices = []
        
        for i in range(total_pages):
            page = doc[i]
            page_text = page.get_text().strip()
            
            if len(page_text) > 100:
                full_text += f"\n--- СТРАНИЦА {i+1} (ТЕКСТ) ---\n{page_text}\n"
            else:
                scanned_page_indices.append(i)
        
        # Если найдены сканированные страницы, обрабатываем их через Vision
        if scanned_page_indices:
            print(f"PDF {pdf_path}: обнаружено {len(scanned_page_indices)} сканированных страниц.")
            
            # Умный выбор страниц для OCR (чтобы не сканировать всё подряд)
            # Приоритет: первые 5, последние 5 и каждая 5-я в середине
            to_ocr = set()
            for idx in scanned_page_indices:
                if idx < 5: to_ocr.add(idx) # Начало
                elif idx >= total_pages - 5: to_ocr.add(idx) # Конец
                elif idx % 5 == 0: to_ocr.add(idx) # Каждая 5-я для средних страниц
            
            # Ограничиваем общее число OCR-запросов (например, до 20 на документ)
            final_ocr_list = sorted(list(to_ocr))[:20]
            
            if final_ocr_list:
                print(f"Выполняется OCR для страниц: {[i+1 for i in final_ocr_list]}")
                ocr_results = extract_text_via_openai_vision(doc, final_ocr_list)
                full_text += ocr_results
            
        doc.close()
    except Exception as e:
        print(f"Ошибка при обработке PDF {pdf_path}: {e}")
        return f"Ошибка: Не удалось извлечь текст ({e})"
    return full_text

def extract_text_via_openai_vision(doc: fitz.Document, pages_to_ocr: list) -> str:
    """Отправляет выбранные страницы в OpenAI Vision для распознавания."""
    if not settings.OPENAI_API_KEY:
        return "\n[Ошибка: OpenAI API Key не настроен для OCR]\n"

    combined_ocr_text = ""
    
    for page_num in pages_to_ocr:
        try:
            page = doc.load_page(page_num)
            # Увеличиваем разрешение для улучшения качества OCR
            pix = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5)) 
            img_data = pix.tobytes("png")
            base64_image = base64.b64encode(img_data).decode('utf-8')

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}"
            }
            
            # Улучшенный промпт для юридических документов
            prompt = (
                "Это страница из юридического договора или акта. "
                "Транскрибируй весь текст максимально точно. "
                "ОБРАТИ ОСОБОЕ ВНИМАНИЕ на таблицы, списки адресов лифтов, ИНН организаций, "
                "суммы (цифрами и прописью) и даты. "
                "Выведи ТОЛЬКО распознанный текст без своих комментариев."
            )

            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{base64_image}"}
                            }
                        ]
                    }
                ],
                "max_tokens": 3000
            }
            
            session = _get_session()
            response = session.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers, timeout=120)
            response.raise_for_status()
            page_text = response.json()['choices'][0]['message']['content']
            combined_ocr_text += f"\n--- СТРАНИЦА {page_num + 1} (OCR) ---\n{page_text}\n"
        except Exception as e:
            print(f"Ошибка OCR на странице {page_num}: {e}")
            combined_ocr_text += f"\n[Ошибка OCR на странице {page_num + 1}]\n"

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

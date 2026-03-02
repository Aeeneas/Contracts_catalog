import os
import shutil
import zipfile
import aiofiles
import hashlib
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Form
from fastapi.responses import JSONResponse, StreamingResponse
from typing import List, Optional
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session

# Улучшенные импорты
try:
    from database import get_db, Contract, Customer
    from config import settings
    from text_extractor import extract_text
    from ai_service import extract_contract_data, summarize_contract
    from contract_utils import generate_unique_contract_number
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from database import get_db, Contract, Customer
    from config import settings
    from text_extractor import extract_text
    from ai_service import extract_contract_data, summarize_contract
    from contract_utils import generate_unique_contract_number

from pydantic import BaseModel, ValidationError, ConfigDict
import json
import re
from starlette.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
import subprocess
import asyncio

def calculate_file_hash(file_path: str) -> str:
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def sanitize_filename(name: str) -> str:
    if not name: return "Unknown"
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
TMP_UPLOAD_DIR = os.path.join(STORAGE_DIR, "tmp")
ARCHIVE_DIR = os.path.join(STORAGE_DIR, "archive")
FINAL_STORAGE_ROOT = os.path.join(STORAGE_DIR, "contracts_final")

os.makedirs(TMP_UPLOAD_DIR, exist_ok=True)
os.makedirs(ARCHIVE_DIR, exist_ok=True)
os.makedirs(FINAL_STORAGE_ROOT, exist_ok=True)

app = FastAPI()

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(status_code=422, content={"detail": exc.errors()})

origins = ["*"]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class ContractResponse(BaseModel):
    id: int
    upload_date: datetime
    unique_contract_number: str
    doc_type: str
    file_hash: Optional[str] = None
    company: str
    customer: str
    customer_id: Optional[int] = None
    work_type: str
    contract_cost: float
    monthly_cost: Optional[float] = None
    work_address: Optional[str] = None
    elevator_addresses: Optional[str] = None
    elevator_count: Optional[int] = 0
    stages_info: str
    short_description: str
    ultra_short_summary: Optional[str] = None
    conclusion_date: date
    start_date: date
    end_date: date
    catalog_path: str
    ai_analysis_status: str
    model_config = ConfigDict(from_attributes=True)

class FinalizeContract(BaseModel):
    temp_path: str
    filename: str
    file_hash: str
    doc_type: str = "ДОГ"
    company: str
    customer: str
    customer_inn: Optional[str] = None
    customer_ogrn: Optional[str] = None
    customer_ceo: Optional[str] = None
    customer_legal_address: Optional[str] = None
    customer_contacts: Optional[str] = None
    customer_bank_details: Optional[str] = None
    work_type: str
    contract_cost: float = 0.0
    monthly_cost: Optional[float] = None
    work_address: Optional[str] = None
    elevator_addresses: Optional[str] = None
    elevator_count: Optional[int] = 0
    conclusion_date: Optional[date] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    stages_info: Optional[str] = "Один этап"
    short_description: Optional[str] = ""
    ultra_short_summary: Optional[str] = None

class ContractUpdate(BaseModel):
    doc_type: Optional[str] = None
    company: Optional[str] = None
    customer: Optional[str] = None
    customer_id: Optional[int] = None
    work_type: Optional[str] = None
    contract_cost: Optional[float] = None
    monthly_cost: Optional[float] = None
    work_address: Optional[str] = None
    elevator_addresses: Optional[str] = None
    elevator_count: Optional[int] = None
    stages_info: Optional[str] = None
    short_description: Optional[str] = None
    ultra_short_summary: Optional[str] = None
    conclusion_date: Optional[date] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

async def process_single_file_stream(file_path: str, filename: str, db: Session):
    try:
        yield {"log": f"📄 Обработка файла: {filename}", "status": "info"}
        file_hash = calculate_file_hash(file_path)
        existing = db.query(Contract).filter(Contract.file_hash == file_hash).first()
        if existing:
            yield {"log": f"🚫 Файл уже существует: {existing.unique_contract_number}", "status": "error"}
            yield {"final_result": {"filename": filename, "status": "duplicate_hash", "error": f"Уже загружен ({existing.unique_contract_number})"}}
            return

        yield {"log": "📑 Извлечение текста (OCR)...", "status": "info"}
        text = extract_text(file_path)
        if "Error: " in text:
            yield {"log": f"❌ Ошибка извлечения текста: {text}", "status": "error"}
            yield {"final_result": {"filename": filename, "status": "failed text extraction", "error": text}}
            return

        yield {"log": "🤖 ИИ-анализ (DeepSeek)...", "status": "info"}
        ai_data = extract_contract_data(text)
        
        inn = ai_data.get("customer_inn")
        if inn:
            yield {"log": f"🏢 Найден ИНН: {inn}. Поиск в базе...", "status": "info"}
            existing_customer = db.query(Customer).filter(Customer.inn == inn).first()
            if existing_customer:
                yield {"log": "✅ Заказчик найден в локальной базе. Подгружаем реквизиты.", "status": "success"}
                ai_data.update({
                    "customer": existing_customer.name, "customer_ogrn": existing_customer.ogrn,
                    "customer_ceo": existing_customer.ceo_name, "customer_legal_address": existing_customer.legal_address,
                    "customer_id": existing_customer.id, "customer_bank_details": existing_customer.bank_details,
                    "customer_contacts": existing_customer.contact_info
                })
        
        yield {"log": "📝 Генерация подробного резюме...", "status": "info"}
        ai_summary = summarize_contract(text)
        
        yield {"log": "🎉 Анализ завершен!", "status": "success"}
        yield {"final_result": {
            "temp_path": file_path, "filename": filename, "file_hash": file_hash, 
            "extracted_data": ai_data, "summary": ai_summary or "", "status": "analyzed"
        }}
    except Exception as e:
        yield {"log": f"💥 Критическая ошибка: {str(e)}", "status": "error"}
        yield {"final_result": {"filename": filename, "status": "failed", "error": str(e)}}

@app.post("/analyze")
async def analyze_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    async def event_generator():
        path = os.path.join(TMP_UPLOAD_DIR, file.filename)
        yield f"data: {json.dumps({'log': f'💾 Загрузка на сервер: {file.filename}', 'status': 'info'})}\n\n"
        async with aiofiles.open(path, "wb") as out:
            while content := await file.read(1024): await out.write(content)
        
        if file.filename.lower().endswith(".zip"):
            yield f"data: {json.dumps({'log': '📦 Распаковка архива...', 'status': 'info'})}\n\n"
            unpack_path = os.path.join(TMP_UPLOAD_DIR, f"upk_{datetime.now().strftime('%H%M%S')}")
            os.makedirs(unpack_path, exist_ok=True)
            try:
                with zipfile.ZipFile(path, 'r') as z: z.extractall(unpack_path)
                shutil.move(path, os.path.join(ARCHIVE_DIR, file.filename))
                files_to_process = []
                for root, _, files in os.walk(unpack_path):
                    for f in files:
                        if f.lower().endswith(('.pdf', '.docx', '.doc', '.xlsx', '.xls')):
                            files_to_process.append(os.path.join(root, f))
                
                yield f"data: {json.dumps({'log': f'📂 Найдено {len(files_to_process)} файлов', 'status': 'info'})}\n\n"
                for f_path in files_to_process:
                    async for event in process_single_file_stream(f_path, os.path.basename(f_path), db):
                        yield f"data: {json.dumps(event)}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'log': f'❌ Ошибка архива: {str(e)}', 'status': 'error'})}\n\n"
        else:
            async for event in process_single_file_stream(path, file.filename, db):
                yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/finalize")
async def finalize_upload(data: FinalizeContract, db: Session = Depends(get_db)):
    if not os.path.exists(data.temp_path): raise HTTPException(status_code=404, detail="Файл не найден")
    try:
        target_customer_id = None
        if data.customer_inn:
            cust = db.query(Customer).filter(Customer.inn == data.customer_inn).first()
            if not cust:
                cust = Customer(
                    name=data.customer, inn=data.customer_inn, ogrn=data.customer_ogrn,
                    ceo_name=data.customer_ceo, legal_address=data.customer_legal_address,
                    contact_info=data.customer_contacts, bank_details=data.customer_bank_details
                )
                db.add(cust); db.flush()
            else:
                cust.name = data.customer or cust.name
                cust.ogrn = data.customer_ogrn or cust.ogrn
                cust.ceo_name = data.customer_ceo or cust.ceo_name
                cust.legal_address = data.customer_legal_address or cust.legal_address
            target_customer_id = cust.id

        conclusion_date = data.conclusion_date or date.today()
        unique_num = generate_unique_contract_number(db, data.doc_type, data.company, conclusion_date)
        f_dir = os.path.join(FINAL_STORAGE_ROOT, sanitize_filename(data.company), sanitize_filename(data.customer), sanitize_filename(data.work_type), str(conclusion_date.year))
        os.makedirs(f_dir, exist_ok=True)
        f_path = os.path.join(f_dir, f"{unique_num}_{data.filename}")
        shutil.move(data.temp_path, f_path)

        new_contract = Contract(
            unique_contract_number=unique_num, doc_type=data.doc_type, file_hash=data.file_hash,
            company=data.company, customer=data.customer, customer_id=target_customer_id,
            work_type=data.work_type, contract_cost=data.contract_cost, monthly_cost=data.monthly_cost,
            work_address=data.work_address, elevator_addresses=data.elevator_addresses,
            elevator_count=data.elevator_count, # НОВОЕ ПОЛЕ
            conclusion_date=conclusion_date, start_date=data.start_date or conclusion_date, 
            end_date=data.end_date or conclusion_date, stages_info=data.stages_info, 
            short_description=data.short_description, ultra_short_summary=data.ultra_short_summary,
            catalog_path=f_path, ai_analysis_status="Завершен"
        )
        db.add(new_contract); db.commit(); db.refresh(new_contract)
        return {"status": "success", "contract_id": new_contract.id, "unique_number": unique_num}
    except Exception as e: 
        db.rollback()
        return JSONResponse(status_code=500, content={"error": str(e)})

class CustomerResponse(BaseModel):
    id: int
    name: str
    inn: str
    ogrn: Optional[str] = None
    ceo_name: Optional[str] = None
    legal_address: Optional[str] = None
    contact_info: Optional[str] = None
    bank_details: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class CustomerDetailResponse(CustomerResponse):
    contracts: List[ContractResponse] = []

@app.get("/customers", response_model=List[CustomerResponse])
async def get_all_customers(db: Session = Depends(get_db)):
    return db.query(Customer).order_by(Customer.name).all()

@app.get("/customers/{cid}", response_model=CustomerDetailResponse)
async def get_customer(cid: int, db: Session = Depends(get_db)):
    cust = db.query(Customer).filter(Customer.id == cid).first()
    if not cust: raise HTTPException(status_code=404, detail="Заказчик не найден")
    return cust

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    inn: Optional[str] = None
    ogrn: Optional[str] = None
    ceo_name: Optional[str] = None
    legal_address: Optional[str] = None
    contact_info: Optional[str] = None
    bank_details: Optional[str] = None

@app.put("/customers/{cid}", response_model=CustomerResponse)
async def update_customer(cid: int, data: CustomerUpdate, db: Session = Depends(get_db)):
    cust = db.query(Customer).filter(Customer.id == cid).first()
    if not cust: raise HTTPException(status_code=404, detail="Заказчик не найден")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items(): setattr(cust, key, value)
    try:
        db.commit(); db.refresh(cust); return cust
    except Exception as e:
        db.rollback(); return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/contracts", response_model=List[ContractResponse])
async def get_all_contracts(db: Session = Depends(get_db)):
    return db.query(Contract).all()

@app.get("/contracts/{cid}", response_model=ContractResponse)
async def get_contract(cid: int, db: Session = Depends(get_db)):
    c = db.query(Contract).filter(Contract.id == cid).first()
    if not c: raise HTTPException(404)
    return c

@app.put("/contracts/{cid}", response_model=ContractResponse)
async def update_contract(cid: int, data: ContractUpdate, db: Session = Depends(get_db)):
    c = db.query(Contract).filter(Contract.id == cid).first()
    if not c: raise HTTPException(404)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items(): setattr(c, key, value)
    try:
        db.commit(); db.refresh(c); return c
    except Exception as e:
        db.rollback(); return JSONResponse(status_code=500, content={"error": str(e)})

@app.delete("/contracts/{cid}")
async def delete_contract(cid: int, db: Session = Depends(get_db)):
    c = db.query(Contract).filter(Contract.id == cid).first()
    if c:
        if c.catalog_path and os.path.exists(c.catalog_path):
            try: os.remove(c.catalog_path)
            except: pass
        db.delete(c); db.commit()
    return {"status": "success"}

@app.post("/contracts/{cid}/open-folder")
async def open_contract_folder(cid: int, db: Session = Depends(get_db)):
    c = db.query(Contract).filter(Contract.id == cid).first()
    if not c or not c.catalog_path: raise HTTPException(404)
    abs_path = os.path.abspath(c.catalog_path)
    if os.path.exists(abs_path):
        subprocess.Popen(['explorer', '/select,', abs_path])
        return {"status": "success"}
    return JSONResponse(status_code=404, content={"error": "not_found"})

@app.post("/reset-system")
async def reset_system(db: Session = Depends(get_db)):
    try:
        db.query(Contract).delete(); db.commit()
        if os.path.exists(FINAL_STORAGE_ROOT):
            shutil.rmtree(FINAL_STORAGE_ROOT); os.makedirs(FINAL_STORAGE_ROOT)
        return {"status": "success"}
    except Exception as e: return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/open-folder")
async def open_storage_folder():
    abs_path = os.path.abspath(FINAL_STORAGE_ROOT)
    if os.path.exists(abs_path): subprocess.Popen(['explorer', abs_path]); return {"status": "success"}
    return JSONResponse(status_code=404, content={"error": "not_found"})

@app.post("/cancel-upload")
async def cancel_upload(data: dict):
    path = data.get("temp_path")
    if path and os.path.exists(path): os.remove(path); return {"status": "success"}
    return {"status": "skipped"}

import uvicorn
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

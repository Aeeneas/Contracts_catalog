import os
import shutil
import zipfile
import aiofiles
import json
import subprocess
import asyncio
from typing import List
from datetime import date, datetime
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session

# Локальные импорты
from database import get_db, Contract, Customer
from config import settings
from text_extractor import extract_text
from ai_service import extract_contract_data, summarize_contract
from contract_utils import generate_unique_contract_number
from utils import calculate_file_hash, sanitize_filename, get_storage_path
from schemas import (
    ContractResponse, FinalizeContract, ContractUpdate, 
    CustomerResponse, CustomerDetailResponse, CustomerUpdate
)

app = FastAPI(title="Contract Catalogizer API")

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Директории
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
TMP_UPLOAD_DIR = os.path.join(STORAGE_DIR, "tmp")
ARCHIVE_DIR = os.path.join(STORAGE_DIR, "archive")
FINAL_STORAGE_ROOT = os.path.join(STORAGE_DIR, "contracts_final")

for d in [TMP_UPLOAD_DIR, ARCHIVE_DIR, FINAL_STORAGE_ROOT]:
    os.makedirs(d, exist_ok=True)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(status_code=422, content={"detail": exc.errors()})

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

async def process_single_file_stream(file_path: str, filename: str, db: Session):
    try:
        yield {"log": f"📄 Файл: {filename}", "status": "info"}
        
        file_hash = calculate_file_hash(file_path)
        existing = db.query(Contract).filter(Contract.file_hash == file_hash).first()
        if existing:
            yield {"log": f"🚫 Уже в базе: {existing.unique_contract_number}", "status": "error"}
            yield {"final_result": {"filename": filename, "status": "duplicate_hash", "error": f"Уже загружен ({existing.unique_contract_number})"}}
            return

        yield {"log": "📑 OCR-обработка...", "status": "info"}
        text = extract_text(file_path)
        
        yield {"log": "🤖 ИИ-анализ...", "status": "info"}
        ai_data = extract_contract_data(text)
        
        inn = ai_data.get("customer_inn")
        if inn:
            cust = db.query(Customer).filter(Customer.inn == inn).first()
            if cust:
                yield {"log": "✅ Реквизиты взяты из базы", "status": "success"}
                ai_data.update({
                    "customer": cust.name, "customer_ogrn": cust.ogrn,
                    "customer_ceo": cust.ceo_name, "customer_legal_address": cust.legal_address,
                    "customer_id": cust.id, "customer_bank_details": cust.bank_details
                })
        
        yield {"log": "📝 Генерация резюме...", "status": "info"}
        summary = summarize_contract(text)
        
        yield {"log": "🎉 Готово", "status": "success"}
        yield {"final_result": {
            "temp_path": file_path, "filename": filename, "file_hash": file_hash, 
            "extracted_data": ai_data, "summary": summary or "", "status": "analyzed"
        }}
    except Exception as e:
        yield {"log": f"❌ Ошибка: {str(e)}", "status": "error"}
        yield {"final_result": {"filename": filename, "status": "failed", "error": str(e)}}

# --- МАРШРУТЫ (CONTRACTS) ---

@app.post("/analyze")
async def analyze_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    async def event_generator():
        path = os.path.join(TMP_UPLOAD_DIR, file.filename)
        yield f"data: {json.dumps({'log': f'💾 Загрузка: {file.filename}', 'status': 'info'})}\n\n"
        
        async with aiofiles.open(path, "wb") as out:
            while content := await file.read(1024): await out.write(content)
        
        if file.filename.lower().endswith(".zip"):
            unpack_path = os.path.join(TMP_UPLOAD_DIR, f"upk_{datetime.now().strftime('%H%M%S')}")
            os.makedirs(unpack_path, exist_ok=True)
            with zipfile.ZipFile(path, 'r') as z: z.extractall(unpack_path)
            shutil.move(path, os.path.join(ARCHIVE_DIR, file.filename))
            
            for root, _, files in os.walk(unpack_path):
                for f in files:
                    if f.lower().endswith(('.pdf', '.docx', '.doc', '.xlsx', '.xls')):
                        async for ev in process_single_file_stream(os.path.join(root, f), f, db):
                            yield f"data: {json.dumps(ev)}\n\n"
        else:
            async for ev in process_single_file_stream(path, file.filename, db):
                yield f"data: {json.dumps(ev)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/finalize")
async def finalize_upload(data: FinalizeContract, db: Session = Depends(get_db)):
    if not os.path.exists(data.temp_path): raise HTTPException(404, "Файл не найден")
    try:
        # Обработка заказчика
        cust_id = None
        if data.customer_inn:
            cust = db.query(Customer).filter(Customer.inn == data.customer_inn).first()
            if not cust:
                cust = Customer(
                    name=data.customer, inn=data.customer_inn, ogrn=data.customer_ogrn,
                    ceo_name=data.customer_ceo, legal_address=data.customer_legal_address,
                    bank_details=data.customer_bank_details
                )
                db.add(cust); db.flush()
            cust_id = cust.id

        # Сохранение файла
        c_date = data.conclusion_date or date.today()
        unique_num = generate_unique_contract_number(db, data.doc_type, data.company, c_date)
        f_dir = get_storage_path(FINAL_STORAGE_ROOT, data.company, data.customer, data.work_type, c_date.year)
        os.makedirs(f_dir, exist_ok=True)
        f_path = os.path.join(f_dir, f"{unique_num}_{data.filename}")
        shutil.move(data.temp_path, f_path)

        # Создание договора
        new_c = Contract(
            unique_contract_number=unique_num, doc_type=data.doc_type, file_hash=data.file_hash,
            company=data.company, customer=data.customer, customer_id=cust_id,
            work_type=data.work_type, contract_cost=data.contract_cost, monthly_cost=data.monthly_cost,
            work_address=data.work_address, elevator_addresses=data.elevator_addresses,
            elevator_count=data.elevator_count, conclusion_date=c_date,
            start_date=data.start_date or c_date, end_date=data.end_date or c_date,
            stages_info=data.stages_info, short_description=data.short_description,
            ultra_short_summary=data.ultra_short_summary, catalog_path=f_path, ai_analysis_status="Завершен"
        )
        db.add(new_c); db.commit(); db.refresh(new_c)
        return {"status": "success", "id": new_c.id}
    except Exception as e:
        db.rollback(); return JSONResponse(500, {"error": str(e)})

@app.get("/contracts", response_model=List[ContractResponse])
def get_contracts(db: Session = Depends(get_db)):
    return db.query(Contract).all()

@app.get("/contracts/{cid}", response_model=ContractResponse)
def get_contract(cid: int, db: Session = Depends(get_db)):
    c = db.query(Contract).filter(Contract.id == cid).first()
    if not c: raise HTTPException(404)
    return c

@app.put("/contracts/{cid}", response_model=ContractResponse)
def update_contract(cid: int, data: ContractUpdate, db: Session = Depends(get_db)):
    c = db.query(Contract).filter(Contract.id == cid).first()
    if not c: raise HTTPException(404)
    for k, v in data.model_dump(exclude_unset=True).items(): setattr(c, k, v)
    db.commit(); return c

@app.delete("/contracts/{cid}")
def delete_contract(cid: int, db: Session = Depends(get_db)):
    c = db.query(Contract).filter(Contract.id == cid).first()
    if c:
        if os.path.exists(c.catalog_path):
            try: os.remove(c.catalog_path)
            except: pass
        db.delete(c); db.commit()
    return {"status": "success"}

# --- МАРШРУТЫ (CUSTOMERS) ---

@app.get("/customers", response_model=List[CustomerResponse])
def get_customers(db: Session = Depends(get_db)):
    return db.query(Customer).order_by(Customer.name).all()

@app.get("/customers/{cid}", response_model=CustomerDetailResponse)
def get_customer(cid: int, db: Session = Depends(get_db)):
    cust = db.query(Customer).filter(Customer.id == cid).first()
    if not cust: raise HTTPException(404)
    return cust

@app.put("/customers/{cid}", response_model=CustomerResponse)
def update_customer(cid: int, data: CustomerUpdate, db: Session = Depends(get_db)):
    cust = db.query(Customer).filter(Customer.id == cid).first()
    if not cust: raise HTTPException(404)
    for k, v in data.model_dump(exclude_unset=True).items(): setattr(cust, k, v)
    db.commit(); return cust

# --- СИСТЕМНЫЕ МАРШРУТЫ ---

@app.post("/contracts/{cid}/open-folder")
def open_folder(cid: int, db: Session = Depends(get_db)):
    c = db.query(Contract).filter(Contract.id == cid).first()
    if not c or not os.path.exists(c.catalog_path): raise HTTPException(404)
    subprocess.Popen(['explorer', '/select,', os.path.abspath(c.catalog_path)])
    return {"status": "success"}

@app.post("/open-folder")
def open_root():
    subprocess.Popen(['explorer', os.path.abspath(FINAL_STORAGE_ROOT)])
    return {"status": "success"}

@app.post("/reset-system")
def reset(db: Session = Depends(get_db)):
    db.query(Contract).delete(); db.query(Customer).delete(); db.commit()
    if os.path.exists(FINAL_STORAGE_ROOT):
        shutil.rmtree(FINAL_STORAGE_ROOT); os.makedirs(FINAL_STORAGE_ROOT)
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

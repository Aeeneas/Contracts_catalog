import os
import shutil
import zipfile
import aiofiles
import hashlib
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Form
from fastapi.responses import JSONResponse
from typing import List, Optional
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
try:
    from database import get_db, Contract, Customer
    from config import settings
    from text_extractor import extract_text
    from ai_service import extract_contract_data, summarize_contract
    from contract_utils import generate_unique_contract_number
except ImportError:
    from .database import get_db, Contract, Customer
    from .config import settings
    from .text_extractor import extract_text
    from .ai_service import extract_contract_data, summarize_contract
    from .contract_utils import generate_unique_contract_number
from pydantic import BaseModel, ValidationError
import json
import re
from starlette.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
import subprocess

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
    print(f"DEBUG Validation Error: {exc.errors()}")
    return JSONResponse(status_code=422, content={"detail": exc.errors()})

origins = ["http://localhost", "http://localhost:3000"]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class CustomerResponse(BaseModel):
    id: int
    name: str
    inn: str
    ogrn: Optional[str]
    ceo_name: Optional[str]
    legal_address: Optional[str]
    contact_info: Optional[str]
    bank_details: Optional[str]
    class Config: from_attributes = True

class ContractResponse(BaseModel):
    id: int
    upload_date: datetime
    unique_contract_number: str
    doc_type: str
    file_hash: Optional[str]
    company: str
    customer: str
    customer_id: Optional[int]
    work_type: str
    work_address: Optional[str]
    elevator_addresses: Optional[str]
    contract_cost: float
    monthly_cost: Optional[float]
    stages_info: str
    short_description: str
    ultra_short_summary: Optional[str]
    conclusion_date: date
    start_date: date
    end_date: date
    catalog_path: str
    ai_analysis_status: str
    class Config: from_attributes = True

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
    work_address: Optional[str] = None
    elevator_addresses: Optional[str] = None
    contract_cost: float = 0.0
    monthly_cost: Optional[float] = None
    conclusion_date: Optional[date] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    stages_info: str = "Один этап"
    short_description: str = ""
    ultra_short_summary: Optional[str] = ""

class ContractUpdate(BaseModel):
    doc_type: Optional[str] = None
    company: Optional[str] = None
    customer: Optional[str] = None
    work_type: Optional[str] = None
    work_address: Optional[str] = None
    elevator_addresses: Optional[str] = None
    contract_cost: Optional[float] = None
    monthly_cost: Optional[float] = None
    conclusion_date: Optional[date] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    stages_info: Optional[str] = None
    short_description: Optional[str] = None
    ultra_short_summary: Optional[str] = None

async def process_single_file(file_path: str, filename: str, db: Session):
    try:
        file_hash = calculate_file_hash(file_path)
        existing = db.query(Contract).filter(Contract.file_hash == file_hash).first()
        if existing: return {"filename": filename, "status": "duplicate_hash", "error": f"Файл уже загружен (Номер: {existing.unique_contract_number})"}
        text = extract_text(file_path)
        if "Error: " in text: return {"filename": filename, "status": "failed text extraction", "error": text}
        ai_data = extract_contract_data(text)
        ai_summary = summarize_contract(text)
        if "error" in ai_data: return {"filename": filename, "status": "failed AI extraction", "error": ai_data["error"]}
        return {"temp_path": file_path, "filename": filename, "file_hash": file_hash, "extracted_data": ai_data, "summary": ai_summary or "", "status": "analyzed"}
    except Exception as e: return {"filename": filename, "status": "failed", "error": str(e)}

@app.post("/analyze")
async def analyze_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    path = os.path.join(TMP_UPLOAD_DIR, file.filename)
    async with aiofiles.open(path, "wb") as out:
        while content := await file.read(1024): await out.write(content)
    if file.filename.lower().endswith(".zip"):
        unpack_path = os.path.join(TMP_UPLOAD_DIR, f"unpack_{datetime.now().strftime('%Y%m%d%H%M%S')}")
        os.makedirs(unpack_path, exist_ok=True)
        try:
            with zipfile.ZipFile(path, 'r') as z: z.extractall(unpack_path)
            shutil.move(path, os.path.join(ARCHIVE_DIR, file.filename))
            results = []
            for root, _, files in os.walk(unpack_path):
                for f in files:
                    if f.lower().endswith(('.pdf', '.docx', '.doc', '.xlsx', '.xls')):
                        results.append(await process_single_file(os.path.join(root, f), f, db))
            return {"status": "batch_analyzed", "results": results}
        except Exception as e: return JSONResponse(status_code=500, content={"error": str(e)})
    else:
        res = await process_single_file(path, file.filename, db)
        return JSONResponse(status_code=400, content=res) if res.get("status") in ["failed", "duplicate_hash"] else res

@app.post("/finalize")
async def finalize_upload(data: FinalizeContract, db: Session = Depends(get_db)):
    if not os.path.exists(data.temp_path): raise HTTPException(status_code=404, detail="Файл не найден")
    try:
        c_date = data.conclusion_date or date.today()
        s_date = data.start_date or c_date
        e_date = data.end_date or (s_date + timedelta(days=365))
        
        customer_id = None
        if data.customer_inn:
            cust = db.query(Customer).filter(Customer.inn == data.customer_inn).first()
            if not cust:
                cust = Customer(
                    name=data.customer, inn=data.customer_inn, ogrn=data.customer_ogrn, 
                    ceo_name=data.customer_ceo, legal_address=data.customer_legal_address, 
                    contact_info=data.customer_contacts, bank_details=data.customer_bank_details
                )
                db.add(cust); db.commit(); db.refresh(cust)
            else:
                if data.customer_ceo: cust.ceo_name = data.customer_ceo
                if data.customer_legal_address: cust.legal_address = data.customer_legal_address
                if data.customer_contacts: cust.contact_info = data.customer_contacts
                db.commit()
            customer_id = cust.id

        unique_num = generate_unique_contract_number(doc_type=data.doc_type, company=data.company, conclusion_date=c_date)
        is_dup = db.query(Contract).filter((Contract.unique_contract_number == unique_num) | (Contract.file_hash == data.file_hash)).first()
        if is_dup: return JSONResponse(status_code=409, content={"error": "duplicate", "message": f"Документ {unique_num} уже существует."})

        f_dir = os.path.join(FINAL_STORAGE_ROOT, sanitize_filename(data.company), sanitize_filename(data.customer), sanitize_filename(data.work_type), str(c_date.year))
        os.makedirs(f_dir, exist_ok=True)
        f_path = os.path.join(f_dir, f"{unique_num}_{data.filename}")
        shutil.move(data.temp_path, f_path)

        new_contract = Contract(
            unique_contract_number=unique_num, doc_type=data.doc_type, file_hash=data.file_hash,
            company=data.company, customer=data.customer, customer_id=customer_id,
            work_type=data.work_type, work_address=data.work_address, elevator_addresses=data.elevator_addresses,
            contract_cost=data.contract_cost, monthly_cost=data.monthly_cost,
            conclusion_date=c_date, start_date=s_date, end_date=e_date,
            stages_info=data.stages_info, short_description=data.short_description,
            ultra_short_summary=data.ultra_short_summary,
            catalog_path=f_path, ai_analysis_status="Completed"
        )
        db.add(new_contract); db.commit(); db.refresh(new_contract)
        return {"status": "success", "contract_id": new_contract.id, "unique_number": unique_num}
    except Exception as e: return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/contracts", response_model=List[ContractResponse])
async def get_all_contracts(db: Session = Depends(get_db)):
    return db.query(Contract).all()

@app.get("/contracts/{contract_id}", response_model=ContractResponse)
async def get_contract_details(contract_id: int, db: Session = Depends(get_db)):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract: raise HTTPException(status_code=404, detail="Not found")
    return contract

@app.get("/customers/{customer_id}", response_model=CustomerResponse)
async def get_customer_details(customer_id: int, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer: raise HTTPException(status_code=404, detail="Customer not found")
    return customer

@app.put("/contracts/{contract_id}", response_model=ContractResponse)
async def update_contract(contract_id: int, updated: ContractUpdate, db: Session = Depends(get_db)):
    db_contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not db_contract: raise HTTPException(status_code=404, detail="Not found")
    old_path = db_contract.catalog_path
    for k, v in updated.model_dump(exclude_unset=True).items(): setattr(db_contract, k, v)
    new_dir = os.path.join(FINAL_STORAGE_ROOT, sanitize_filename(db_contract.company), sanitize_filename(db_contract.customer), sanitize_filename(db_contract.work_type), str(db_contract.conclusion_date.year))
    os.makedirs(new_dir, exist_ok=True)
    new_path = os.path.join(new_dir, os.path.basename(old_path))
    if old_path != new_path and os.path.exists(old_path):
        shutil.move(old_path, new_path)
        db_contract.catalog_path = new_path
    db.commit(); db.refresh(db_contract)
    return db_contract

@app.delete("/contracts/{contract_id}")
async def delete_contract(contract_id: int, db: Session = Depends(get_db)):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract: raise HTTPException(status_code=404, detail="Not found")
    if contract.catalog_path and os.path.exists(contract.catalog_path):
        try: os.remove(contract.catalog_path)
        except: pass
    db.delete(contract); db.commit()
    return {"status": "success"}

@app.post("/open-folder")
async def open_storage_folder():
    abs_path = os.path.abspath(FINAL_STORAGE_ROOT)
    if os.path.exists(abs_path): subprocess.Popen(['explorer', abs_path]); return {"status": "success"}
    return JSONResponse(status_code=404, content={"error": "not_found"})

@app.post("/contracts/{contract_id}/open-folder")
async def open_contract_folder(contract_id: int, db: Session = Depends(get_db)):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if contract and contract.catalog_path:
        folder_path = os.path.dirname(os.path.abspath(contract.catalog_path))
        if os.path.exists(folder_path): subprocess.Popen(['explorer', folder_path]); return {"status": "success"}
    return JSONResponse(status_code=404, content={"error": "not_found"})

@app.post("/cancel-upload")
async def cancel_upload(data: dict):
    path = data.get("temp_path")
    if path and os.path.exists(path): os.remove(path); return {"status": "success"}
    return {"status": "skipped"}

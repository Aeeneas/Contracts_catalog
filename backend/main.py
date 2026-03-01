import os
import shutil
import zipfile
import aiofiles
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Form
from fastapi.responses import JSONResponse
from typing import List, Optional
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
try:
    from database import get_db, Contract
    from config import settings
    from text_extractor import extract_text
    from ai_service import extract_contract_data, summarize_contract
    from contract_utils import generate_unique_contract_number
except ImportError:
    from .database import get_db, Contract
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

def sanitize_filename(name: str) -> str:
    """Удаляет символы, запрещенные в именах файлов и папок Windows."""
    if not name:
        return "Unknown"
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
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
    )

origins = ["http://localhost", "http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ContractBase(BaseModel):
    unique_contract_number: str
    doc_type: str = "ДОГ"
    company: str
    customer: str
    work_type: str
    contract_cost: float
    monthly_cost: Optional[float] = None
    stages_info: str = "Один этап"
    short_description: str
    conclusion_date: date
    start_date: date
    end_date: date
    catalog_path: str
    ai_analysis_status: str = "В ожидании"

class ContractCreate(ContractBase):
    pass

class ContractResponse(BaseModel):
    id: int
    upload_date: datetime
    unique_contract_number: str
    doc_type: str
    company: str
    customer: str
    work_type: str
    contract_cost: float
    monthly_cost: Optional[float]
    stages_info: str
    short_description: str
    conclusion_date: date
    start_date: date
    end_date: date
    catalog_path: str
    ai_analysis_status: str

    class Config:
        from_attributes = True

class FinalizeContract(BaseModel):
    temp_path: str
    filename: str
    doc_type: Optional[str] = "ДОГ"
    company: Optional[str] = None
    customer: Optional[str] = None
    work_type: Optional[str] = None
    contract_cost: Optional[float] = 0.0
    monthly_cost: Optional[float] = None
    conclusion_date: Optional[date] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    stages_info: Optional[str] = "Один этап"
    short_description: Optional[str] = ""

class ContractUpdate(BaseModel):
    doc_type: Optional[str] = None
    company: Optional[str] = None
    customer: Optional[str] = None
    work_type: Optional[str] = None
    contract_cost: Optional[float] = None
    monthly_cost: Optional[float] = None
    conclusion_date: Optional[date] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    stages_info: Optional[str] = None
    short_description: Optional[str] = None

async def process_single_file(file_path: str, filename: str, db: Session):
    try:
        extracted_text = extract_text(file_path)
        if "Error: " in extracted_text:
            return {"filename": filename, "status": "failed text extraction", "error": extracted_text}

        ai_extracted_data = extract_contract_data(extracted_text)
        ai_summary = summarize_contract(extracted_text)

        if "error" in ai_extracted_data:
            return {"filename": filename, "status": "failed AI extraction", "error": ai_extracted_data["error"]}

        return {
            "temp_path": file_path,
            "filename": filename,
            "extracted_data": ai_extracted_data,
            "summary": ai_summary or "Не удалось сгенерировать описание.",
            "status": "analyzed"
        }
    except Exception as e:
        return {"filename": filename, "status": "failed", "error": str(e)}

@app.post("/analyze")
async def analyze_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    file_path_in_tmp = os.path.join(TMP_UPLOAD_DIR, file.filename)
    async with aiofiles.open(file_path_in_tmp, "wb") as out_file:
        while content := await file.read(1024):
            await out_file.write(content)
    
    if file.filename.lower().endswith(".zip"):
        unpack_dir_name = f"unpack_{datetime.now().strftime('%Y%m%d%H%M%S')}_{os.path.splitext(file.filename)[0]}"
        unpack_path = os.path.join(TMP_UPLOAD_DIR, unpack_dir_name)
        os.makedirs(unpack_path, exist_ok=True)
        try:
            with zipfile.ZipFile(file_path_in_tmp, 'r') as zip_ref:
                zip_ref.extractall(unpack_path)
            archive_path = os.path.join(ARCHIVE_DIR, file.filename)
            shutil.move(file_path_in_tmp, archive_path)
            results = []
            for root, dirs, files in os.walk(unpack_path):
                for f in files:
                    if f.lower().endswith(('.pdf', '.docx', '.doc', '.xlsx', '.xls')):
                        full_f_path = os.path.join(root, f)
                        res = await process_single_file(full_f_path, f, db)
                        results.append(res)
            return {"status": "batch_analyzed", "results": results}
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": f"Ошибка архива: {str(e)}"})
    else:
        res = await process_single_file(file_path_in_tmp, file.filename, db)
        return JSONResponse(status_code=400, content=res) if res.get("status") == "failed" else res

@app.post("/finalize")
async def finalize_upload(data: FinalizeContract, db: Session = Depends(get_db)):
    if not os.path.exists(data.temp_path):
        raise HTTPException(status_code=404, detail=f"Файл не найден: {data.temp_path}")
    try:
        conclusion_date = data.conclusion_date or date.today()
        start_date = data.start_date or conclusion_date
        end_date = data.end_date or (start_date + timedelta(days=365))

        if not all([data.company, data.customer, data.work_type]):
             return JSONResponse(status_code=400, content={"error": "missing_fields", "message": "Обязательные поля не заполнены."})

        unique_num = generate_unique_contract_number(
            doc_type=data.doc_type or "ДОГ",
            company=data.company,
            conclusion_date=conclusion_date
        )

        is_duplicate = db.query(Contract).filter(
            Contract.unique_contract_number == unique_num,
            Contract.company == data.company,
            Contract.customer == data.customer,
            Contract.conclusion_date == conclusion_date
        ).first()

        if is_duplicate:
            return JSONResponse(status_code=409, content={"error": "duplicate", "message": f"Документ {unique_num} уже существует."})

        final_dir_path = os.path.join(FINAL_STORAGE_ROOT, sanitize_filename(data.company), sanitize_filename(data.customer), sanitize_filename(data.work_type), str(conclusion_date.year))
        os.makedirs(final_dir_path, exist_ok=True)
        final_file_path = os.path.join(final_dir_path, f"{unique_num}_{data.filename}")
        shutil.move(data.temp_path, final_file_path)

        contract_db_data = {
            "unique_contract_number": unique_num,
            "doc_type": data.doc_type or "ДОГ",
            "company": data.company,
            "customer": data.customer,
            "work_type": data.work_type,
            "contract_cost": data.contract_cost,
            "monthly_cost": data.monthly_cost,
            "conclusion_date": conclusion_date,
            "start_date": start_date,
            "end_date": end_date,
            "stages_info": data.stages_info,
            "short_description": data.short_description,
            "catalog_path": final_file_path,
            "ai_analysis_status": "Completed"
        }
        db_contract = Contract(**contract_db_data)
        db.add(db_contract)
        db.commit()
        db.refresh(db_contract)
        return {"status": "success", "contract_id": db_contract.id, "unique_number": unique_num}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/contracts", response_model=List[ContractResponse])
async def get_all_contracts(db: Session = Depends(get_db)):
    return db.query(Contract).all()

@app.get("/contracts/{contract_id}", response_model=ContractResponse)
async def get_contract_details(contract_id: int, db: Session = Depends(get_db)):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract: raise HTTPException(status_code=404, detail="Contract not found")
    return contract

@app.put("/contracts/{contract_id}", response_model=ContractResponse)
async def update_contract(contract_id: int, updated_data: ContractUpdate, db: Session = Depends(get_db)):
    db_contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not db_contract: raise HTTPException(status_code=404, detail="Договор не найден")
    
    old_path = db_contract.catalog_path
    for key, value in updated_data.model_dump(exclude_unset=True).items():
        setattr(db_contract, key, value)

    new_dir_path = os.path.join(FINAL_STORAGE_ROOT, sanitize_filename(db_contract.company), sanitize_filename(db_contract.customer), sanitize_filename(db_contract.work_type), str(db_contract.conclusion_date.year))
    os.makedirs(new_dir_path, exist_ok=True)
    new_file_path = os.path.join(new_dir_path, os.path.basename(old_path))
    if old_path != new_file_path and os.path.exists(old_path):
        shutil.move(old_path, new_file_path)
        db_contract.catalog_path = new_file_path

    db.commit()
    db.refresh(db_contract)
    return db_contract

@app.delete("/contracts/{contract_id}")
async def delete_contract(contract_id: int, db: Session = Depends(get_db)):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract: raise HTTPException(status_code=404, detail="Договор не найден")
    if contract.catalog_path and os.path.exists(contract.catalog_path):
        try: os.remove(contract.catalog_path)
        except: pass
    db.delete(contract)
    db.commit()
    return {"status": "success"}

@app.post("/open-folder")
async def open_storage_folder():
    abs_path = os.path.abspath(FINAL_STORAGE_ROOT)
    if os.path.exists(abs_path):
        subprocess.Popen(['explorer', abs_path])
        return {"status": "success"}
    return JSONResponse(status_code=404, content={"error": "not_found"})

@app.post("/contracts/{contract_id}/open-folder")
async def open_contract_folder(contract_id: int, db: Session = Depends(get_db)):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if contract and contract.catalog_path:
        folder_path = os.path.dirname(os.path.abspath(contract.catalog_path))
        if os.path.exists(folder_path):
            subprocess.Popen(['explorer', folder_path])
            return {"status": "success"}
    return JSONResponse(status_code=404, content={"error": "not_found"})

@app.post("/cancel-upload")
async def cancel_upload(data: dict):
    path = data.get("temp_path")
    if path and os.path.exists(path):
        os.remove(path)
        return {"status": "success"}
    return {"status": "skipped"}

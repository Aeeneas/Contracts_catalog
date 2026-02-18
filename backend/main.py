import os
import shutil
import zipfile
import aiofiles
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Form
from fastapi.responses import JSONResponse
from typing import List, Optional
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from database import get_db, Contract
from config import settings
from text_extractor import extract_text
from ai_service import extract_contract_data, summarize_contract
from contract_utils import generate_unique_contract_number
from pydantic import BaseModel, ValidationError
import json
import re # Добавлен импорт re
from starlette.middleware.cors import CORSMiddleware # Добавленный импорт для CORS

def sanitize_filename(name: str) -> str:
    """Удаляет символы, запрещенные в именах файлов и папок Windows."""
    if not name:
        return "Unknown"
    # Удаляем кавычки, двоеточия, звездочки и т.д.
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

# Определяем пути для хранения файлов
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
TMP_UPLOAD_DIR = os.path.join(STORAGE_DIR, "tmp")
ARCHIVE_DIR = os.path.join(STORAGE_DIR, "archive")
FINAL_STORAGE_ROOT = os.path.join(STORAGE_DIR, "contracts_final") # Новая корневая папка для финального хранения

# Убедимся, что директории существуют
os.makedirs(TMP_UPLOAD_DIR, exist_ok=True)
os.makedirs(ARCHIVE_DIR, exist_ok=True)
os.makedirs(FINAL_STORAGE_ROOT, exist_ok=True) # Создаем финальную папку

app = FastAPI()

# Добавляем middleware для обработки CORS
origins = [
    "http://localhost",
    "http://localhost:3000",  # Порт, на котором обычно работает React dev server
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic модели для валидации данных API
class ContractBase(BaseModel):
    unique_contract_number: str
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

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Contract Catalogizer API"}

@app.post("/upload")
async def upload_documents(files: List[UploadFile] = File(...), db: Session = Depends(get_db)):
    """
    Handles document uploads, saves them to a temporary directory,
    and unpacks ZIP archives, moving original ZIPs to an archive directory.
    Extracts text from non-ZIP files and performs AI analysis for contract data.
    Generates a unique contract number, checks for duplicates, and saves to DB.
    """
    processed_files_info = []
    
    for uploaded_file in files:
        file_path_in_tmp = os.path.join(TMP_UPLOAD_DIR, uploaded_file.filename)
        current_file_status = "pending"

        try:
            # Сохраняем файл во временную директорию
            async with aiofiles.open(file_path_in_tmp, "wb") as out_file:
                while content := await uploaded_file.read(1024):
                    await out_file.write(content)
            
            # Обработка ZIP-файлов
            if uploaded_file.filename.lower().endswith(".zip"):
                unpack_dir_name = os.path.splitext(uploaded_file.filename)[0]
                unpack_path = os.path.join(TMP_UPLOAD_DIR, unpack_dir_name)
                os.makedirs(unpack_path, exist_ok=True)
                
                with zipfile.ZipFile(file_path_in_tmp, 'r') as zip_ref:
                    zip_ref.extractall(unpack_path)
                
                # Перемещаем оригинальный ZIP-файл в архивную директорию
                archive_file_path = os.path.join(ARCHIVE_DIR, uploaded_file.filename)
                shutil.move(file_path_in_tmp, archive_file_path)
                
                processed_files_info.append({"filename": uploaded_file.filename, "status": "unpacked and archived", "unpacked_to": unpack_path})
                current_file_status = "unpacked"
                # TODO: Рекурсивно обрабатывать извлеченные файлы, здесь только основная логика
                
            else: # Для не-ZIP файлов
                extracted_text = extract_text(file_path_in_tmp)
                
                if "Error: " in extracted_text:
                    processed_files_info.append({"filename": uploaded_file.filename, "status": "failed text extraction", "error": extracted_text})
                    current_file_status = "failed"
                    # Optionally, remove file that failed text extraction
                    # os.remove(file_path_in_tmp)
                    continue
                
                # 1.3 Интеграция с AI (Gemini API)
                ai_extracted_data = extract_contract_data(extracted_text)
                ai_summary = summarize_contract(extracted_text)

                if "error" in ai_extracted_data:
                    processed_files_info.append({"filename": uploaded_file.filename, "status": "failed AI extraction", "error": ai_extracted_data["error"]})
                    current_file_status = "failed"
                    # os.remove(file_path_in_tmp)
                    continue
                
                if not ai_summary:
                    ai_summary = "Не удалось сгенерировать краткое описание AI."

                # Преобразование данных и применение логики по умолчанию
                try:
                    # Преобразование дат из строк в объекты date
                    conclusion_date_obj = date.fromisoformat(ai_extracted_data["conclusion_date"]) if ai_extracted_data.get("conclusion_date") else None
                    start_date_obj = date.fromisoformat(ai_extracted_data["start_date"]) if ai_extracted_data.get("start_date") else None
                    end_date_obj = date.fromisoformat(ai_extracted_data["end_date"]) if ai_extracted_data.get("end_date") else None

                    # Применение правил по умолчанию для дат
                    if not conclusion_date_obj:
                         raise ValueError("Conclusion date is mandatory and not found by AI.")
                    
                    if not start_date_obj:
                        start_date_obj = conclusion_date_obj
                    
                    if not end_date_obj:
                        end_date_obj = start_date_obj + timedelta(days=365) # 12 месяцев
                    
                    # 1.4 Генерация уникального номера договора
                    unique_num = generate_unique_contract_number(
                        work_type=ai_extracted_data.get("work_type", ""),
                        company=ai_extracted_data.get("company", ""),
                        conclusion_date=conclusion_date_obj
                    )

                    # Подготовка данных для создания контракта
                    contract_data = {
                        "unique_contract_number": unique_num,
                        "company": ai_extracted_data.get("company"),
                        "customer": ai_extracted_data.get("customer"),
                        "work_type": ai_extracted_data.get("work_type"),
                        "contract_cost": float(ai_extracted_data.get("contract_cost", 0.0)),
                        "monthly_cost": float(ai_extracted_data.get("monthly_cost")) if ai_extracted_data.get("monthly_cost") else None,
                        "stages_info": ai_extracted_data.get("stages_info") if ai_extracted_data.get("stages_info") else "Один этап",
                        "short_description": ai_summary,
                        "conclusion_date": conclusion_date_obj,
                        "start_date": start_date_obj,
                        "end_date": end_date_obj,
                        "catalog_path": "", # Будет заполнено после перемещения в финальное хранилище
                        "ai_analysis_status": "Completed"
                    }

                    # Проверяем обязательные поля
                    if not all([contract_data["company"], contract_data["customer"], contract_data["work_type"], contract_data["contract_cost"] is not None, contract_data["conclusion_date"], contract_data["unique_contract_number"]]):
                         raise ValueError("AI failed to extract all mandatory contract fields or unique number generation failed.")

                    # 1.5 Проверка на дубликаты
                    # Более комплексная проверка на дубликаты
                    is_duplicate = db.query(Contract).filter(
                        Contract.unique_contract_number == contract_data["unique_contract_number"],
                        Contract.company == contract_data["company"],
                        Contract.customer == contract_data["customer"],
                        Contract.conclusion_date == contract_data["conclusion_date"]
                        # Добавил unique_contract_number для более точной проверки
                    ).first()
                    
                    if is_duplicate:
                        processed_files_info.append({
                            "filename": uploaded_file.filename,
                            "status": "duplicate detected",
                            "message": f"Contract with unique number {is_duplicate.unique_contract_number} already exists (ID: {is_duplicate.id}). Skipping insertion.",
                            "extracted_data": contract_data
                        })
                        current_file_status = "duplicate"
                        # Удаляем временный файл, так как он не будет сохранен
                        os.remove(file_path_in_tmp) 
                        continue

                    # 1.6 Формирование файловой структуры и перемещение файлов
                    final_dir_path = os.path.join(
                        FINAL_STORAGE_ROOT,
                        sanitize_filename(contract_data["company"]),
                        sanitize_filename(contract_data["customer"]),
                        sanitize_filename(contract_data["work_type"]),
                        str(contract_data["conclusion_date"].year)
                    )
                    os.makedirs(final_dir_path, exist_ok=True)
                    
                    final_file_name = f"{contract_data['unique_contract_number']}_{uploaded_file.filename}"
                    final_file_path = os.path.join(final_dir_path, final_file_name)
                    shutil.move(file_path_in_tmp, final_file_path)
                    
                    contract_data["catalog_path"] = final_file_path # Обновляем путь в данных
                    
                    # 1.7 Сохранение данных в БД
                    new_contract = ContractCreate(**contract_data)
                    db_contract = Contract(**new_contract.model_dump())
                    db.add(db_contract)
                    db.commit()
                    db.refresh(db_contract)

                    processed_files_info.append({
                        "filename": uploaded_file.filename,
                        "status": "successfully processed and saved",
                        "contract_id": db_contract.id,
                        "unique_contract_number": db_contract.unique_contract_number,
                        "final_path": db_contract.catalog_path
                    })
                    current_file_status = "success"

                except (ValueError, ValidationError, json.JSONDecodeError) as ve:
                    processed_files_info.append({"filename": uploaded_file.filename, "status": "failed AI data processing or unique ID generation", "error": str(ve)})
                    current_file_status = "failed"
                    # os.remove(file_path_in_tmp) # Удаляем временный файл при ошибке обработки
                    continue

        except Exception as e:
            processed_files_info.append({"filename": uploaded_file.filename, "status": "failed", "error": str(e)})
            current_file_status = "failed"
            # if os.path.exists(file_path_in_tmp):
            #     os.remove(file_path_in_tmp) # Удаляем временный файл при общей ошибке
            
        finally:
            # Очистка временного файла, если он все еще существует и не был перемещен
            if current_file_status not in ["success", "unpacked", "duplicate"] and os.path.exists(file_path_in_tmp):
                os.remove(file_path_in_tmp)
    
    return JSONResponse(
        status_code=200,
        content={"message": "Files processed", "details": processed_files_info}
    )

@app.get("/contracts", response_model=List[ContractResponse])
async def get_all_contracts(db: Session = Depends(get_db), skip: int = 0, limit: int = 100):
    """
    Retrieves a list of all contracts.
    """
    contracts = db.query(Contract).offset(skip).limit(limit).all()
    return contracts

@app.get("/contracts/{contract_id}", response_model=ContractResponse)
async def get_contract_details(contract_id: int, db: Session = Depends(get_db)):
    """
    Retrieves details for a specific contract by its ID.
    """
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if contract is None:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract

@app.post("/contracts", response_model=List[ContractResponse]) # Изменено для приема списка контрактов
async def create_multiple_contracts(contracts: List[ContractCreate], db: Session = Depends(get_db)):
    """
    Creates multiple new contract entries in the database.
    This endpoint can be used for bulk insertion or after batch processing.
    """
    created_contracts = []
    for contract in contracts:
        # Применяем значения по умолчанию, если они не предоставлены
        if not contract.start_date:
            contract.start_date = contract.conclusion_date
        if not contract.end_date:
            contract.end_date = contract.start_date + timedelta(days=365) # Приблизительно 12 месяцев

        # Расширенная проверка на дубликаты
        existing_contract = db.query(Contract).filter(
            Contract.unique_contract_number == contract.unique_contract_number,
            Contract.company == contract.company,
            Contract.customer == contract.customer,
            Contract.conclusion_date == contract.conclusion_date
        ).first()

        if existing_contract:
            raise HTTPException(status_code=400, detail=f"Contract with unique number {contract.unique_contract_number} already exists.")

        db_contract = Contract(**contract.model_dump())
        db.add(db_contract)
        db.commit()
        db.refresh(db_contract)
        created_contracts.append(db_contract)
    return created_contracts


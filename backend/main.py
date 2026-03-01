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

from fastapi.exceptions import RequestValidationError

import subprocess

app = FastAPI()

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    print(f"DEBUG Validation Error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
    )

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

@app.post("/analyze")
async def analyze_document(file: UploadFile = File(...)):
    """
    Только анализирует документ, извлекает текст и данные ИИ.
    Не сохраняет в базу данных и не перемещает в финальное хранилище.
    """
    file_path_in_tmp = os.path.join(TMP_UPLOAD_DIR, file.filename)
    
    try:
        # Сохраняем файл во временную директорию
        async with aiofiles.open(file_path_in_tmp, "wb") as out_file:
            while content := await file.read(1024):
                await out_file.write(content)
        
        extracted_text = extract_text(file_path_in_tmp)
        if "Error: " in extracted_text:
            return JSONResponse(status_code=400, content={"error": "failed text extraction", "details": extracted_text})

        ai_extracted_data = extract_contract_data(extracted_text)
        ai_summary = summarize_contract(extracted_text)

        if "error" in ai_extracted_data:
            return JSONResponse(status_code=400, content={"error": "failed AI extraction", "details": ai_extracted_data["error"]})

        # Дополняем данными для фронтенда
        result = {
            "temp_path": file_path_in_tmp,
            "filename": file.filename,
            "extracted_data": ai_extracted_data,
            "summary": ai_summary or "Не удалось сгенерировать описание."
        }
        
        return result

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

class FinalizeContract(BaseModel):
    temp_path: str
    filename: str
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

@app.post("/finalize")
async def finalize_upload(data: FinalizeContract, db: Session = Depends(get_db)):
    """
    Принимает подтвержденные пользователем данные, генерирует номер,
    перемещает файл и сохраняет в БД.
    """
    print(f"DEBUG: Received finalize data: {data.model_dump()}")
    
    if not os.path.exists(data.temp_path):
        raise HTTPException(status_code=404, detail=f"Временный файл не найден: {data.temp_path}")

    try:
        # Установка дат по умолчанию, если они не заполнены
        conclusion_date = data.conclusion_date or date.today()
        start_date = data.start_date or conclusion_date
        end_date = data.end_date or (start_date + timedelta(days=365))

        # 1. Проверка критических полей
        if not all([data.company, data.customer, data.work_type]):
             return JSONResponse(status_code=400, content={"error": "missing_fields", "message": "Компания, Заказчик и Тип работ обязательны для заполнения."})

        # 2. Генерация уникального номера договора
        unique_num = generate_unique_contract_number(
            work_type=data.work_type,
            company=data.company,
            conclusion_date=conclusion_date
        )

        # 3. Проверка на дубликаты
        is_duplicate = db.query(Contract).filter(
            Contract.unique_contract_number == unique_num,
            Contract.company == data.company,
            Contract.customer == data.customer,
            Contract.conclusion_date == conclusion_date
        ).first()

        if is_duplicate:
            return JSONResponse(status_code=409, content={
                "error": "duplicate detected",
                "message": f"Договор с номером {unique_num} уже существует (ID: {is_duplicate.id})."
            })

        # 4. Формирование файловой структуры
        final_dir_path = os.path.join(
            FINAL_STORAGE_ROOT,
            sanitize_filename(data.company),
            sanitize_filename(data.customer),
            sanitize_filename(data.work_type),
            str(conclusion_date.year)
        )
        os.makedirs(final_dir_path, exist_ok=True)
        
        final_file_name = f"{unique_num}_{data.filename}"
        final_file_path = os.path.join(final_dir_path, final_file_name)
        
        # Перемещаем файл из TMP в финальное место
        shutil.move(data.temp_path, final_file_path)

        # 5. Сохранение в БД
        contract_db_data = {
            "unique_contract_number": unique_num,
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
        # В случае ошибки стараемся не удалять файл, чтобы пользователь мог попробовать еще раз
        # (или логика очистки по таймеру)
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/contracts/{contract_id}/open-folder")
async def open_contract_folder(contract_id: int, db: Session = Depends(get_db)):
    """
    Открывает папку, в которой хранится файл конкретного договора.
    """
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Договор не найден")
    
    if not contract.catalog_path:
        raise HTTPException(status_code=400, detail="Путь к файлу не указан")

    try:
        # Получаем путь к директории из полного пути к файлу
        folder_path = os.path.dirname(os.path.abspath(contract.catalog_path))
        
        if os.path.exists(folder_path):
            subprocess.Popen(['explorer', folder_path])
            return {"status": "success", "message": f"Папка открыта: {folder_path}"}
        else:
            return JSONResponse(status_code=404, content={"error": "folder_not_found", "message": "Папка договора не найдена на диске."})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/open-folder")
async def open_storage_folder():
    """
    Открывает папку с финальными договорами в проводнике Windows поверх остальных окон.
    """
    try:
        abs_path = os.path.abspath(FINAL_STORAGE_ROOT)
        if os.path.exists(abs_path):
            # Использование subprocess для запуска проводника напрямую
            # Это часто помогает окну оказаться в фокусе (на переднем плане)
            subprocess.Popen(['explorer', abs_path])
            return {"status": "success", "message": f"Папка открыта: {abs_path}"}
        else:
            return JSONResponse(status_code=404, content={"error": "folder_not_found", "message": "Папка хранилища еще не создана."})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/cancel-upload")
async def cancel_upload(data: dict):
    """
    Удаляет временный файл, если пользователь отменил сохранение.
    """
    temp_path = data.get("temp_path")
    if temp_path and os.path.exists(temp_path):
        try:
            os.remove(temp_path)
            return {"status": "success", "message": "Временный файл удален"}
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})
    return {"status": "skipped", "message": "Файл не найден или путь не указан"}

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

class ContractUpdate(BaseModel):
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

@app.delete("/contracts/{contract_id}")
async def delete_contract(contract_id: int, db: Session = Depends(get_db)):
    """
    Удаляет договор из базы данных и соответствующий файл с диска.
    """
    db_contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not db_contract:
        raise HTTPException(status_code=404, detail="Договор не найден")

    # Удаляем физический файл, если он существует
    file_path = db_contract.catalog_path
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"Ошибка при удалении файла {file_path}: {e}")
            # Мы продолжаем удаление из БД, даже если файл не удалось удалить

    # Удаляем запись из БД
    db.delete(db_contract)
    db.commit()
    
    return {"status": "success", "message": f"Договор {contract_id} и файл удалены"}

@app.put("/contracts/{contract_id}", response_model=ContractResponse)
async def update_contract(contract_id: int, updated_data: ContractUpdate, db: Session = Depends(get_db)):
    """
    Обновляет данные договора и перемещает файл, если изменились ключевые поля.
    """
    db_contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not db_contract:
        raise HTTPException(status_code=404, detail="Договор не найден")

    # Сохраняем старые данные для проверки необходимости перемещения файла
    old_company = db_contract.company
    old_customer = db_contract.customer
    old_work_type = db_contract.work_type
    old_year = db_contract.conclusion_date.year
    old_path = db_contract.catalog_path

    # Обновляем поля в объекте БД
    update_dict = updated_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(db_contract, key, value)

    # Проверяем, нужно ли перемещать файл (если изменились ключевые метаданные)
    new_year = db_contract.conclusion_date.year
    meta_changed = (
        old_company != db_contract.company or
        old_customer != db_contract.customer or
        old_work_type != db_contract.work_type or
        old_year != new_year
    )

    if meta_changed and old_path and os.path.exists(old_path):
        try:
            # Формируем новый путь
            new_dir_path = os.path.join(
                FINAL_STORAGE_ROOT,
                sanitize_filename(db_contract.company),
                sanitize_filename(db_contract.customer),
                sanitize_filename(db_contract.work_type),
                str(new_year)
            )
            os.makedirs(new_dir_path, exist_ok=True)
            
            file_name = os.path.basename(old_path)
            # Если изменился номер договора (может понадобиться регенерация, но пока оставим старый префикс)
            new_file_path = os.path.join(new_dir_path, file_name)
            
            if old_path != new_file_path:
                shutil.move(old_path, new_file_path)
                db_contract.catalog_path = new_file_path
        except Exception as e:
            print(f"Ошибка при перемещении файла: {e}")
            # Продолжаем сохранение в БД даже если файл не удалось переместить

    db.commit()
    db.refresh(db_contract)
    return db_contract

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


from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import date, datetime

class ContractBase(BaseModel):
    doc_type: str = "ДОГ"
    company: str
    customer: str
    customer_id: Optional[int] = None
    work_type: str
    contract_cost: float = 0.0
    monthly_cost: Optional[float] = None
    work_address: Optional[str] = None
    elevator_addresses: Optional[str] = None
    elevator_count: int = 0
    conclusion_date: Optional[date] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    stages_info: Optional[str] = "Один этап"
    short_description: Optional[str] = ""
    ultra_short_summary: Optional[str] = None

class ContractResponse(ContractBase):
    id: int
    upload_date: datetime
    unique_contract_number: str
    file_hash: Optional[str] = None
    catalog_path: str
    ai_analysis_status: str
    model_config = ConfigDict(from_attributes=True)

class FinalizeContract(ContractBase):
    temp_path: str
    filename: str
    file_hash: str
    customer_inn: Optional[str] = None
    customer_ogrn: Optional[str] = None
    customer_ceo: Optional[str] = None
    customer_legal_address: Optional[str] = None
    customer_contacts: Optional[str] = None
    customer_bank_details: Optional[str] = None

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

class CustomerBase(BaseModel):
    name: str
    inn: str
    ogrn: Optional[str] = None
    ceo_name: Optional[str] = None
    legal_address: Optional[str] = None
    contact_info: Optional[str] = None
    bank_details: Optional[str] = None

class CustomerResponse(CustomerBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class CustomerDetailResponse(CustomerResponse):
    contracts: List[ContractResponse] = []

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    inn: Optional[str] = None
    ogrn: Optional[str] = None
    ceo_name: Optional[str] = None
    legal_address: Optional[str] = None
    contact_info: Optional[str] = None
    bank_details: Optional[str] = None

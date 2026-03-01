from datetime import date
from sqlalchemy.orm import Session
import re

# Маппинг типов документов для номера
DOC_TYPE_MAP = {
    "ДОГ": "ДОГ",
    "ДС": "ДС",
    "АКТ": "АКТ",
    "КС-2": "КС2",
    "КС-3": "КС3"
}

def generate_unique_contract_number(db: Session, doc_type: str, company: str, conclusion_date: date) -> str:
    """
    Генерирует уникальный номер: [Тип]-[Префикс]-[Год]-[Порядковый номер]
    Пример: ДОГ-ТЛ-2026-001
    """
    from database import Contract # Импорт внутри для избежания циклической зависимости

    # 1. Код документа
    doc_code = DOC_TYPE_MAP.get(doc_type.upper() if doc_type else "ДОГ", "ДОГ")
    
    # 2. Префикс компании
    comp_upper = str(company or "").upper()
    if "ТОР-ЛИФТ" in comp_upper or "ТОР ЛИФТ" in comp_upper:
        prefix = "ТЛ"
    elif "ПРОТИВОВЕС-Т" in comp_upper:
        prefix = "ПВТ"
    elif "ПРОТИВОВЕС" in comp_upper:
        prefix = "ПВ"
    else:
        prefix = "ПР" # Прочее

    # 3. Год (берем из даты договора или текущий)
    year_str = str(conclusion_date.year) if conclusion_date else str(date.today().year)

    # 4. Ищем последний номер в базе для этого шаблона
    pattern = f"{doc_code}-{prefix}-{year_str}-%"
    last_contract = db.query(Contract.unique_contract_number)\
        .filter(Contract.unique_contract_number.like(pattern))\
        .order_by(Contract.unique_contract_number.desc())\
        .first()

    next_num = 1
    if last_contract:
        # Извлекаем число из конца строки (ДОГ-ТЛ-2026-005 -> 5)
        match = re.search(r'-(\d+)$', last_contract[0])
        if match:
            next_num = int(match.group(1)) + 1

    # Форматируем номер с ведущими нулями (001, 002...)
    return f"{doc_code}-{prefix}-{year_str}-{next_num:03d}"

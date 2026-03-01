from datetime import date

# Маппинг типов документов для номера
DOC_TYPE_MAP = {
    "ДОГ": "ДОГ",
    "ДС": "ДС",
    "АКТ": "АКТ",
    "КС-2": "КС2",
    "КС-3": "КС3"
}

# Префиксы компаний согласно ТЗ
COMPANY_PREFIXES = {
    "ТОР-ЛИФТ": "ТЛ",
    "ПРОТИВОВЕС": "ПВ",
    "ПРОТИВОВЕС-Т": "ПВТ"
}

def generate_unique_contract_number(doc_type: str, company: str, conclusion_date: date) -> str:
    """
    Генерирует уникальный номер согласно формату: [Тип док]-[Префикс]-[ММГГ]
    Пример: ДОГ-ТЛ-0126
    """
    
    # Определяем код документа (по умолчанию ДОГ)
    doc_code = DOC_TYPE_MAP.get(doc_type.upper(), "ДОГ")
    
    # Определяем префикс компании
    comp_upper = company.upper()
    if "ТОР-ЛИФТ" in comp_upper or "ТОР ЛИФТ" in comp_upper:
        prefix = "ТЛ"
    elif "ПРОТИВОВЕС-Т" in comp_upper:
        prefix = "ПВТ"
    elif "ПРОТИВОВЕС" in comp_upper:
        prefix = "ПВ"
    else:
        prefix = "??"

    # Формируем ММГГ
    date_part = conclusion_date.strftime("%m%y")

    return f"{doc_code}-{prefix}-{date_part}"

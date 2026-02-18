from datetime import date

# Define mappings for abbreviations
WORK_TYPE_ABBREVIATIONS = {
    "ТО": "ТХ",
    "МОНТАЖ": "МН",
    "СТРОЙКА": "СТ",
    "ПРОЕКТИРОВАНИЕ": "ПР",
    "КАПИТАЛЬНЫЕ РАБОТЫ": "КР"
}

COMPANY_ABBREVIATIONS = {
    "Противовес": "ПВ",
    "Противовес-Т": "ПВТ",
    "ТОР-ЛИФТ": "ТЛ"
}

def generate_unique_contract_number(work_type: str, company: str, conclusion_date: date) -> str:
    """
    Generates a unique contract number based on the specified format.
    Format: [Аббревиатура_Типа_работ]-[Аббревиатура_Компании]-[Месяц_подписания][Год_подписания]
    Example: МН-ПВ-0726 (Монтаж-Противовес-Июль 2026)
    """
    
    # Get work type abbreviation
    work_type_abbr = WORK_TYPE_ABBREVIATIONS.get(work_type.upper(), "??")
    
    # Get company abbreviation
    company_abbr = COMPANY_ABBREVIATIONS.get(company.upper(), "??")
    # Handle variations for "Противовес"
    if "ПРОТИВОВЕС-Т" in company.upper():
        company_abbr = "ПВТ"
    elif "ПРОТИВОВЕС" in company.upper():
        company_abbr = "ПВ"
    elif "ТОР-ЛИФТ" in company.upper():
        company_abbr = "ТЛ"
    else:
        company_abbr = "??" # If not recognized

    # Get month and year from conclusion date
    month_str = conclusion_date.strftime("%m")
    year_str = conclusion_date.strftime("%y") # Last two digits of the year

    return f"{work_type_abbr}-{company_abbr}-{month_str}{year_str}"

# Example usage
if __name__ == "__main__":
    test_date = date(2026, 7, 15)
    print(generate_unique_contract_number("МОНТАЖ", "Противовес", test_date)) # Expected: МН-ПВ-0726
    print(generate_unique_contract_number("КАПИТАЛЬНЫЕ РАБОТЫ", "ТОР-ЛИФТ", date(2025, 1, 1))) # Expected: КР-ТЛ-0125
    print(generate_unique_contract_number("ТО", "Противовес-Т", date(2024, 12, 31))) # Expected: ТХ-ПВТ-1224
    print(generate_unique_contract_number("СТРОЙКА", "Неизвестная Компания", date(2023, 5, 10))) # Expected: СТ-??-0523

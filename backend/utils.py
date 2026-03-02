import hashlib
import re
import os

def calculate_file_hash(file_path: str) -> str:
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def sanitize_filename(name: str) -> str:
    if not name: return "Unknown"
    name = re.sub(r'[\/*?:"<>|]', "", name)
    return name.strip()

def get_storage_path(base_dir: str, company: str, customer: str, work_type: str, year: int) -> str:
    path = os.path.join(
        base_dir, 
        sanitize_filename(company), 
        sanitize_filename(customer), 
        sanitize_filename(work_type), 
        str(year)
    )
    return path

def validate_inn(inn: str) -> bool:
    """Проверка ИНН на корректность контрольной суммы."""
    if not inn or not inn.isdigit():
        return False
    
    inn_len = len(inn)
    if inn_len not in (10, 12):
        return False

    def get_check_digit(inn_val, coefficients):
        s = sum(int(digit) * coeff for digit, coeff in zip(inn_val, coefficients))
        return str((s % 11) % 10)

    if inn_len == 10:
        # Для 10-значного ИНН (юрлица)
        coeffs = (2, 4, 10, 3, 5, 9, 4, 6, 8)
        return inn[-1] == get_check_digit(inn, coeffs)
    
    elif inn_len == 12:
        # Для 12-значного ИНН (ИП и физлица)
        coeffs1 = (7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
        coeffs2 = (3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
        check1 = get_check_digit(inn[:11], coeffs1)
        check2 = get_check_digit(inn, coeffs2)
        return inn[10] == check1 and inn[11] == check2

    return False

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
    # Удаляем запрещенные символы для Windows и Linux
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

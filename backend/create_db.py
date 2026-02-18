import os
import sys

# Добавляем родительскую директорию (backend) в путь Python
# Это позволит относительным импортам внутри пакета работать при запуске скрипта напрямую
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import create_db_tables
from config import settings

if __name__ == "__main__":
    print("Attempting to create database tables...")
    create_db_tables()
    print("Database tables created (if they didn't exist).")

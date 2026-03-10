from database import engine
from sqlalchemy import text

def update():
    print("Обновление базы данных...")
    columns_to_add = [
        ("elevator_count", "INTEGER DEFAULT 0"),
        ("ultra_short_summary", "VARCHAR(255)"),
        ("ai_analysis_status", "VARCHAR(50) DEFAULT 'В ожидании'"),
        ("parent_id", "INTEGER REFERENCES contracts(id)"),
        ("customer_id", "INTEGER REFERENCES customers(id)")
    ]
    
    for col_name, col_type in columns_to_add:
        try:
            with engine.begin() as conn: # engine.begin() starts a transaction and commits at the end
                conn.execute(text(f"ALTER TABLE contracts ADD COLUMN {col_name} {col_type}"))
                print(f"Колонка {col_name} успешно добавлена.")
        except Exception as e:
            if "already exists" in str(e).lower() or "существует" in str(e).lower():
                print(f"Колонка {col_name} уже существует.")
            else:
                print(f"Ошибка при добавлении {col_name}: {e}")
                
    print("Обновление завершено.")

if __name__ == "__main__":
    update()

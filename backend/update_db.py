from database import engine
from sqlalchemy import text

def update():
    print("Обновление базы данных...")
    try:
        with engine.connect() as conn:
            # Пытаемся добавить колонку elevator_count
            conn.execute(text("ALTER TABLE contracts ADD COLUMN elevator_count INTEGER DEFAULT 0"))
            conn.commit()
            print("Колонка elevator_count успешно добавлена.")
    except Exception as e:
        if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
            print("Колонка уже существует, обновление не требуется.")
        else:
            print(f"Ошибка при обновлении: {e}")

if __name__ == "__main__":
    update()

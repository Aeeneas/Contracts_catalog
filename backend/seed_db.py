from datetime import date, timedelta, datetime
from sqlalchemy.orm import Session
from database import SessionLocal, Contract, create_db_tables
from contract_utils import generate_unique_contract_number # Assuming this is available

# Ensure tables are created before seeding (optional, but good for fresh runs)
create_db_tables()

# Helper function to get a DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Dummy data for contracts
dummy_contracts_data = [
    {
        "company": "ТОР-ЛИФТ",
        "customer": "ООО 'Альфа-Строй'",
        "work_type": "МОНТАЖ",
        "contract_cost": 1500000.00,
        "monthly_cost": None,
        "stages_info": "Один этап",
        "short_description": "Монтаж лифтового оборудования в жилом комплексе.",
        "conclusion_date": date(2023, 1, 15),
        "start_date": date(2023, 1, 15),
        "end_date": date(2023, 7, 15),
        "catalog_path": "/path/to/docs/torlift_alfastroy_montazh_2023.pdf",
        "ai_analysis_status": "Completed"
    },
    {
        "company": "Противовес",
        "customer": "ТЦ 'Мегаполис'",
        "work_type": "ТО",
        "contract_cost": 60000.00,
        "monthly_cost": 5000.00,
        "stages_info": "Один этап",
        "short_description": "Ежемесячное техническое обслуживание эскалаторов.",
        "conclusion_date": date(2024, 2, 1),
        "start_date": date(2024, 2, 1),
        "end_date": date(2025, 1, 31),
        "catalog_path": "/path/to/docs/protivoves_megapolis_to_2024.pdf",
        "ai_analysis_status": "Completed"
    },
    {
        "company": "Противовес-Т",
        "customer": "ЖК 'Солнечный'",
        "work_type": "КАПИТАЛЬНЫЕ РАБОТЫ",
        "contract_cost": 2500000.00,
        "monthly_cost": None,
        "stages_info": "Один этап",
        "short_description": "Капитальный ремонт лифтов в трех секциях ЖК.",
        "conclusion_date": date(2023, 11, 1),
        "start_date": date(2023, 11, 1),
        "end_date": date(2024, 5, 1),
        "catalog_path": "/path/to/docs/protivoves_t_solnechny_kapremont_2023.pdf",
        "ai_analysis_status": "Completed"
    },
    {
        "company": "ТОР-ЛИФТ",
        "customer": "НИИ 'Прогресс'",
        "work_type": "ПРОЕКТИРОВАНИЕ",
        "contract_cost": 300000.00,
        "monthly_cost": None,
        "stages_info": "Техническое задание, Эскизный проект, Рабочая документация",
        "short_description": "Проектирование грузовых лифтов для нового корпуса НИИ.",
        "conclusion_date": date(2024, 3, 10),
        "start_date": date(2024, 3, 10),
        "end_date": date(2024, 6, 10),
        "catalog_path": "/path/to/docs/torlift_nii_proektirovanie_2024.pdf",
        "ai_analysis_status": "Completed"
    },
    {
        "company": "Противовес",
        "customer": "Музей 'Искусство'",
        "work_type": "МОНТАЖ",
        "contract_cost": 800000.00,
        "monthly_cost": None,
        "stages_info": "Один этап",
        "short_description": "Монтаж панорамного лифта в здании музея.",
        "conclusion_date": date(2024, 4, 5),
        "start_date": date(2024, 4, 5),
        "end_date": date(2024, 9, 5),
        "catalog_path": "/path/to/docs/protivoves_museum_montazh_2024.pdf",
        "ai_analysis_status": "Completed"
    },
    {
        "company": "ТОР-ЛИФТ",
        "customer": "Гос.Учреждение 'Развитие'",
        "work_type": "ТО",
        "contract_cost": 96000.00,
        "monthly_cost": 8000.00,
        "stages_info": "Один этап",
        "short_description": "Годовой контракт на обслуживание 12 лифтов.",
        "conclusion_date": date(2025, 1, 1),
        "start_date": date(2025, 1, 1),
        "end_date": date(2025, 12, 31),
        "catalog_path": "/path/to/docs/torlift_gosuchrezhdenie_to_2025.pdf",
        "ai_analysis_status": "Completed"
    },
    {
        "company": "Противовес-Т",
        "customer": "Завод 'Металлург'",
        "work_type": "СТРОЙКА",
        "contract_cost": 4000000.00,
        "monthly_cost": None,
        "stages_info": "Фундамент, Возведение шахты, Установка оборудования",
        "short_description": "Строительство грузовой шахты для промышленного лифта.",
        "conclusion_date": date(2024, 6, 20),
        "start_date": date(2024, 6, 20),
        "end_date": date(2025, 6, 20),
        "catalog_path": "/path/to/docs/protivoves_t_metallurg_stroika_2024.pdf",
        "ai_analysis_status": "Completed"
    },
    {
        "company": "Противовес",
        "customer": "Бизнес Центр 'Вертикаль'",
        "work_type": "КАПИТАЛЬНЫЕ РАБОТЫ",
        "contract_cost": 3200000.00,
        "monthly_cost": None,
        "stages_info": "Один этап",
        "short_description": "Модернизация лифтового оборудования в 15-этажном здании.",
        "conclusion_date": date(2023, 9, 1),
        "start_date": date(2023, 9, 1),
        "end_date": date(2024, 3, 1),
        "catalog_path": "/path/to/docs/protivoves_vertikal_kapremont_2023.pdf",
        "ai_analysis_status": "Completed"
    },
    {
        "company": "ТОР-ЛИФТ",
        "customer": "Частный дом 'Особняк'",
        "work_type": "МОНТАЖ",
        "contract_cost": 650000.00,
        "monthly_cost": None,
        "stages_info": "Один этап",
        "short_description": "Монтаж пассажирского лифта в частном доме.",
        "conclusion_date": date(2025, 3, 1),
        "start_date": date(2025, 3, 1),
        "end_date": date(2025, 6, 1),
        "catalog_path": "/path/to/docs/torlift_osobnyak_montazh_2025.pdf",
        "ai_analysis_status": "Completed"
    },
    {
        "company": "Противовес-Т",
        "customer": "Школа №123",
        "work_type": "ТО",
        "contract_cost": 72000.00,
        "monthly_cost": 6000.00,
        "stages_info": "Один этап",
        "short_description": "Ежеквартальное обслуживание 6 лифтов в школе.",
        "conclusion_date": date(2024, 1, 1),
        "start_date": date(2024, 1, 1),
        "end_date": date(2024, 12, 31),
        "catalog_path": "/path/to/docs/protivoves_t_school_to_2024.pdf",
        "ai_analysis_status": "Completed"
    }
]

def seed_database():
    db: Session = next(get_db()) # Get a database session
    try:
        # Optional: Clear existing data before seeding to ensure a fresh set
        # For a production environment, you might want a more sophisticated upsert logic
        db.query(Contract).delete()
        db.commit()
        print("Cleared existing contract data.")

        for data in dummy_contracts_data:
            # Generate unique_contract_number if not already in data (or override if seeding)
            if "unique_contract_number" not in data:
                data["unique_contract_number"] = generate_unique_contract_number(
                    work_type=data["work_type"],
                    company=data["company"],
                    conclusion_date=data["conclusion_date"]
                )
            
            # Ensure all dates are datetime.date objects
            for key in ["conclusion_date", "start_date", "end_date"]:
                if isinstance(data[key], datetime):
                    data[key] = data[key].date() # Convert datetime to date if necessary

            new_contract = Contract(**data)
            db.add(new_contract)
            print(f"Added contract: {new_contract.unique_contract_number}")
        
        db.commit()
        print("Database seeded successfully with dummy data.")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()

from sqlalchemy import create_engine, Column, Integer, String, Numeric, Date, DateTime, Text
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
from config import settings

DATABASE_URL = settings.DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Contract(Base):
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, index=True)
    unique_contract_number = Column(String(50), unique=True, nullable=False)
    company = Column(String(100), nullable=False)
    customer = Column(String(255), nullable=False)
    work_type = Column(String(50), nullable=False)
    contract_cost = Column(Numeric(15, 2), nullable=False)
    monthly_cost = Column(Numeric(15, 2), nullable=True) # Nullable
    stages_info = Column(Text, nullable=False, default='Один этап')
    short_description = Column(Text, nullable=False)
    conclusion_date = Column(Date, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    catalog_path = Column(Text, unique=True, nullable=False)
    upload_date = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    ai_analysis_status = Column(String(50), nullable=False, default='В ожидании')

    # Optional: Add __repr__ for better debugging
    def __repr__(self):
        return f"<Contract(id={self.id}, unique_contract_number='{self.unique_contract_number}', company='{self.company}', customer='{self.customer}')>"

# Function to create all tables
def create_db_tables():
    Base.metadata.create_all(bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
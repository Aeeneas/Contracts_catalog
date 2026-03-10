from sqlalchemy import create_engine, Column, Integer, String, Numeric, Date, DateTime, Text, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, backref
from datetime import datetime
from config import settings

DATABASE_URL = settings.DATABASE_URL

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    inn = Column(String(12), unique=True, index=True, nullable=False)
    ogrn = Column(String(15), nullable=True)
    ceo_name = Column(String(255), nullable=True)
    legal_address = Column(Text, nullable=True)
    contact_info = Column(Text, nullable=True)
    bank_details = Column(Text, nullable=True)
    
    contracts = relationship("Contract", back_populates="customer_rel")

class Contract(Base):
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, index=True)
    unique_contract_number = Column(String(50), unique=True, nullable=False)
    doc_type = Column(String(20), nullable=False, default='ДОГ')
    file_hash = Column(String(64), nullable=True, index=True)
    company = Column(String(100), nullable=False)
    customer = Column(String(255), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    
    work_type = Column(String(50), nullable=False)
    contract_cost = Column(Numeric(15, 2), nullable=False)
    monthly_cost = Column(Numeric(15, 2), nullable=True)
    
    work_address = Column(Text, nullable=True)
    elevator_addresses = Column(Text, nullable=True)
    elevator_count = Column(Integer, nullable=True, default=0)
    
    stages_info = Column(Text, nullable=False, default='Один этап')
    short_description = Column(Text, nullable=False)
    ultra_short_summary = Column(String(255), nullable=True) # Сверхкраткое описание
    conclusion_date = Column(Date, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    catalog_path = Column(Text, unique=True, nullable=False)
    upload_date = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    ai_analysis_status = Column(String(50), nullable=False, default='В ожидании')

    parent_id = Column(Integer, ForeignKey("contracts.id"), nullable=True)

    customer_rel = relationship("Customer", back_populates="contracts")
    children = relationship("Contract", backref=backref('parent', remote_side=[id]))

    def __repr__(self):
        return f"<Contract(id={self.id}, number='{self.unique_contract_number}', customer='{self.customer}')>"

def create_db_tables():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

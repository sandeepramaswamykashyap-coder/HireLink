import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from backend.utils.logger import logger

# Database Path
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'sqlite')
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)
DB_PATH = os.path.join(DB_DIR, 'local.db')
DATABASE_URL = f"sqlite:///{DB_PATH}"

Base = declarative_base()

class Job(Base):
    __tablename__ = 'jobs'
    
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    location = Column(String)
    salary = Column(String)
    description = Column(Text)
    skills = Column(String)  # Stored as comma-separated string or JSON
    url = Column(String, unique=True, nullable=False)
    source = Column(String)  # e.g., 'naukri', 'linkedin'
    posted_date = Column(DateTime)
    scraped_date = Column(DateTime, default=datetime.utcnow)
    is_easy_apply = Column(Boolean, default=False)
    
    def __repr__(self):
        return f"<Job(title='{self.title}', company='{self.company}', source='{self.source}')>"

class Resume(Base):
    __tablename__ = 'resumes'
    
    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String)
    phone = Column(String)
    raw_text = Column(Text)
    parsed_data = Column(JSON)  # Structured extracted data
    file_path = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class Application(Base):
    __tablename__ = 'applications'
    
    id = Column(Integer, primary_key=True)
    job_id = Column(Integer)
    resume_id = Column(Integer)
    status = Column(String, default="Applied") # Applied, Viewed, Interview, Offer, Rejected, Failed
    applied_at = Column(DateTime, default=datetime.utcnow)
    match_score = Column(Float)
    screenshot_path = Column(String)

class AppUser(Base):
    __tablename__ = 'app_user'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String)
    is_onboarded = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class PortalStatus(Base):
    __tablename__ = 'portal_status'
    
    id = Column(Integer, primary_key=True)
    portal_name = Column(String, unique=True)
    last_scraped = Column(DateTime)
    total_jobs_found = Column(Integer, default=0)
    status = Column(String) # Active, Down, RateLimited

# Setup Database
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    logger.info(f"Initializing database at {DB_PATH}")
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully.")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

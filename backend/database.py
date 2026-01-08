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
    __tablename__ = 'users_v2'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String)
    is_onboarded = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Enhanced Profile Fields
    curr_loc = Column(String)
    linkedin = Column(String)
    website = Column(String)
    github = Column(String)
    
    # Preferences
    target_roles = Column(String) # JSON or Comma-separated
    target_cities = Column(String)
    skip_companies = Column(String)
    work_mode = Column(String) # Remote, Hybrid, Onsite
    instructions = Column(Text)

class QuestionAnswer(Base):
    __tablename__ = 'question_answers'
    id = Column(Integer, primary_key=True)
    question = Column(String, unique=True) # Normalized text or keyword
    answer = Column(String)
    category = Column(String) # e.g., 'experience', 'personal', 'legal'

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
    
    # SEED DEFAULT QUESTIONS if empty
    db = SessionLocal()
    try:
        if db.query(QuestionAnswer).count() == 0:
            defaults = [
                # --- PERSONAL ---
                {"question": "Gender", "answer": "Male", "category": "personal"},
                {"question": "What is your gender", "answer": "Male", "category": "personal"},
                {"question": "Marital Status", "answer": "Single", "category": "personal"},
                {"question": "Are you a veteran", "answer": "No", "category": "personal"},
                {"question": "Do you have a disability", "answer": "No", "category": "personal"},
                {"question": "Hispanic/Latino", "answer": "No", "category": "personal"},
                {"question": "Race", "answer": "Asian", "category": "personal"},

                # --- EMPLOYMENT & NOTICE ---
                {"question": "Notice Period", "answer": "15 Days", "category": "employment"},
                {"question": "How soon can you join", "answer": "Immediately", "category": "employment"},
                {"question": "Current CTC", "answer": "1000000", "category": "employment"},
                {"question": "Current Salary", "answer": "1000000", "category": "employment"},
                {"question": "Expected CTC", "answer": "1500000", "category": "employment"},
                {"question": "Expected Salary", "answer": "1500000", "category": "employment"},
                {"question": "Are you currently employed", "answer": "Yes", "category": "employment"},
                {"question": "Current Company", "answer": "Tech Solutions Inc", "category": "employment"},

                # --- EXPERIENCE ---
                {"question": "Total Experience", "answer": "5", "category": "experience"},
                {"question": "Years of Experience", "answer": "5", "category": "experience"},
                {"question": "Relevant Experience", "answer": "5", "category": "experience"},
                {"question": "Management Experience", "answer": "No", "category": "experience"},
                {"question": "work experience", "answer": "5", "category": "experience"},

                # --- EDUCATION ---
                {"question": "Highest Degree", "answer": "Bachelor's Degree", "category": "education"},
                {"question": "Education Level", "answer": "Bachelor's Degree", "category": "education"},
                {"question": "Have you completed a bachelor's decree", "answer": "Yes", "category": "education"},
                {"question": "Have you completed a master's degree", "answer": "No", "category": "education"},
                {"question": "Graduation Year", "answer": "2020", "category": "education"},
                {"question": "GPA", "answer": "3.8", "category": "education"},

                # --- LEGAL & COMPLIANCE ---
                {"question": "Are you legally authorized to work in", "answer": "Yes", "category": "legal"},
                {"question": "Do you require sponsorship", "answer": "No", "category": "legal"},
                {"question": "Will you now or in the future require sponsorship", "answer": "No", "category": "legal"},
                {"question": "US Citizen", "answer": "No", "category": "legal"},
                {"question": "Background Check", "answer": "Yes", "category": "legal"},
                {"question": "Drug Test", "answer": "Yes", "category": "legal"},
                {"question": "Felony", "answer": "No", "category": "legal"},

                # --- LOGISTICS ---
                {"question": "Are you willing to relocate", "answer": "Yes", "category": "logistics"},
                {"question": "Remote work", "answer": "Yes", "category": "logistics"},
                {"question": "Hybrid work", "answer": "Yes", "category": "logistics"},
                {"question": "When can you start", "answer": "Immediately", "category": "logistics"},
                {"question": "Shift", "answer": "Day", "category": "logistics"},
                
                # --- SKILLS (General) ---
                {"question": "Python", "answer": "5", "category": "skills"},
                {"question": "Java", "answer": "3", "category": "skills"},
                {"question": "SQL", "answer": "4", "category": "skills"},
                {"question": "AWS", "answer": "3", "category": "skills"}
            ]
            for q in defaults:
                db.add(QuestionAnswer(question=q['question'], answer=q['answer'], category=q['category']))
            db.commit()
            logger.info("Seeded default smart answers.")
    except Exception as e:
        logger.error(f"Error seeding defaults: {e}")
    finally:
        db.close()
            
    logger.info("Database initialized successfully.")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

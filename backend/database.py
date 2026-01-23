import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, JSON, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from backend.utils.logger import logger

# Database Path
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'sqlite')
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)
DB_PATH = os.path.join(DB_DIR, 'local.db')

# Logic: Use Env Var (Prod) else Local SQLite
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

# Fix for Railway/Heroku using old 'postgres://' dialect
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

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
    user_id = Column(Integer) # ForeignKey('users_v2.id') - simplified
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
    password = Column(String) # ADDED
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
    
    # Subscription
    subscription_plan = Column(String, default="TRIAL") # STARTER, PRO, PRO_PLUS, TRIAL
    subscription_expiry = Column(DateTime) # Expiry date for the plan
    used_coupon_code = Column(String) # Track which coupon they used
    
    # --- AFFILIATE FIELDS ---
    referral_code = Column(String, unique=True) # Their own code to share
    referred_by_id = Column(Integer) # ID of user who referred them
    earnings_balance = Column(Float, default=0.0) # Wallet
    referral_count = Column(Integer, default=0) # Quick count
    payout_method = Column(String) # UPI/Bank details
    
    # Password Reset
    reset_token = Column(String)
    reset_token_expiry = Column(DateTime)

    def set_password(self, plain_password):
        import hashlib
        # Generate a random salt
        salt = os.urandom(32).hex()
        # Hash the password with the salt
        key = hashlib.pbkdf2_hmac(
            'sha256', 
            plain_password.encode('utf-8'), 
            salt.encode('utf-8'), 
            100000
        )
        # Store as salt$dash
        self.password = f"{salt}${key.hex()}"

    def check_password(self, plain_password):
        import hashlib
        try:
            if not self.password or '$' not in self.password:
                # Fallback for legacy plain text passwords (auto-migrate on login could be added here, but for now just check equality)
                return self.password == plain_password
            
            salt, stored_hash = self.password.split('$')
            key = hashlib.pbkdf2_hmac(
                'sha256', 
                plain_password.encode('utf-8'), 
                salt.encode('utf-8'), 
                100000
            )
            return key.hex() == stored_hash
        except Exception as e:
            logger.error(f"Password check failed: {e}")
            return False


class ReferralTransaction(Base):
    __tablename__ = 'referral_transactions'
    id = Column(Integer, primary_key=True)
    referrer_id = Column(Integer) # Recipient of commission
    referee_id = Column(Integer)  # User who paid
    amount = Column(Float)
    transaction_type = Column(String, default="COMMISSION") # COMMISSION, PAYOUT
    status = Column(String, default="PENDING") # PENDING, COMPLETED, VOID
    occurred_at = Column(DateTime, default=datetime.utcnow)

class Coupon(Base):
    __tablename__ = 'coupons'
    code = Column(String, primary_key=True)
    discount_percent = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class QuestionAnswer(Base):
    __tablename__ = 'question_answers'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users_v2.id')) # ADDED
    question = Column(String) # Removed unique constraint to allow multiple users to answer same Q
    answer = Column(String)
    category = Column(String) # e.g., 'experience', 'personal', 'legal'

class PortalStatus(Base):
    __tablename__ = 'portal_status'
    
    id = Column(Integer, primary_key=True)
    portal_name = Column(String, unique=True)
    last_scraped = Column(DateTime)
    total_jobs_found = Column(Integer, default=0)
    status = Column(String) # Active, Down, RateLimited

# ...
class ActivityLog(Base):
    __tablename__ = 'activity_logs'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users_v2.id'))
    action = Column(String) # Login, Logout, Applied, Updated Profile
    details = Column(String) # Metadata
    timestamp = Column(DateTime, default=datetime.utcnow)

class PortalCredential(Base):
    __tablename__ = 'portal_credentials'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users_v2.id'))
    portal_name = Column(String)
    username = Column(String)
    password = Column(String) # Stored plainly for MVP as per user context
    updated_at = Column(DateTime, default=datetime.utcnow)

class MarketingCampaign(Base):
    __tablename__ = 'marketing_campaigns'
    id = Column(Integer, primary_key=True)
    name = Column(String) # e.g., "Day 1: Welcome"
    subject = Column(String)
    body_template = Column(String) # HTML Template
    day_offset = Column(Integer) # Send on Day X
    # For now, simplistic sequence logic

class UserCampaignStatus(Base):
    __tablename__ = 'user_campaign_status'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users_v2.id'))
    campaign_id = Column(Integer, ForeignKey('marketing_campaigns.id'))
    sent_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="Sent") # Sent, Opened, Clicked (Future)

# Setup Database
if "sqlite" in DATABASE_URL:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

from sqlalchemy import inspect, text # Add text import

def migrate_db():
    """
    Auto-migration to fix schema drift using Inspector to avoid transaction abuse.
    """
    try:
        inspector = inspect(engine)
        if inspector.has_table("users_v2"):
            columns = [c['name'] for c in inspector.get_columns("users_v2")]
            
            # --- USERS_V2 MIGRATIONS ---
            if "password" not in columns:
                logger.info("Migration: 'password' column missing in users_v2. Adding it.")
                with engine.connect() as conn:
                    with conn.begin(): # Transaction
                        conn.execute(text("ALTER TABLE users_v2 ADD COLUMN password VARCHAR"))
                logger.info("Migration: Successfully added 'password' column.")
            
            if "subscription_expiry" not in columns:
                logger.info("Migration: 'subscription_expiry' column missing in users_v2. Adding it.")
                with engine.connect() as conn:
                    with conn.begin(): # Transaction
                        # Use TIMESTAMP which is standard SQL (Postgres compatible)
                        conn.execute(text("ALTER TABLE users_v2 ADD COLUMN subscription_expiry DATETIME"))
                logger.info("Migration: Successfully added 'subscription_expiry' column.")
            
            if "reset_token" not in columns:
                logger.info("Migration: 'reset_token' column missing in users_v2. Adding it.")
                with engine.connect() as conn:
                    with conn.begin(): # Transaction
                        conn.execute(text("ALTER TABLE users_v2 ADD COLUMN reset_token VARCHAR"))
                logger.info("Migration: Successfully added 'reset_token' column.")
            
            if "reset_token_expiry" not in columns:
                logger.info("Migration: 'reset_token_expiry' column missing in users_v2. Adding it.")
                with engine.connect() as conn:
                    with conn.begin(): # Transaction
                        conn.execute(text("ALTER TABLE users_v2 ADD COLUMN reset_token_expiry TIMESTAMP"))
                logger.info("Migration: Successfully added 'reset_token_expiry' column.")

        # --- Q&A PRIVACY MIGRATIONS ---
        if inspector.has_table("question_answers"):
            columns = [c['name'] for c in inspector.get_columns("question_answers")]
            if "user_id" not in columns:
                logger.info("Migration: 'user_id' missing in question_answers. Adding it.")
                with engine.connect() as conn:
                    with conn.begin():
                        conn.execute(text("ALTER TABLE question_answers ADD COLUMN user_id INTEGER"))
        
        # --- APPLICATION PRIVACY MIGRATIONS ---
        if inspector.has_table("applications"):
             columns = [c['name'] for c in inspector.get_columns("applications")]
             if "user_id" not in columns:
                 logger.info("Migration: 'user_id' check on applications.")
                 with engine.connect() as conn:
                    with conn.begin():
                        conn.execute(text("ALTER TABLE applications ADD COLUMN user_id INTEGER"))

        # --- FIX: DROP STALE UNIQUE CONSTRAINT (Postgres) ---
        # The 'question' column should NOT be unique globally, as multiple users have the same questions.
        if engine.dialect.name == 'postgresql':
            try:
                with engine.connect() as conn:
                    with conn.begin():
                        conn.execute(text("ALTER TABLE question_answers DROP CONSTRAINT IF EXISTS question_answers_question_key"))
                logger.info("Migration: Dropped stale unique constraint 'question_answers_question_key'.")
            except Exception as e:
                # Often fails if constraint doesn't exist, which is fine.
                logger.warning(f"Migration: Attempted to drop constraint but failed (ignorable): {e}")

    except Exception as e:
        logger.warning(f"Migration check failed: {e}")

# Default Questions List (Shared)
DEFAULT_SMART_ANSWERS = [
    # --- PERSONAL INFORMATION ---
    {"question": "Full legal name (first, middle, last)", "answer": "", "category": "personal"},
    {"question": "Preferred name or nickname", "answer": "", "category": "personal"},
    {"question": "Date of birth", "answer": "", "category": "personal"},
    {"question": "Gender (options: Male, Female, Non-binary, Prefer not to say)", "answer": "", "category": "personal"},
    {"question": "Nationality / Country of citizenship", "answer": "", "category": "personal"},
    {"question": "Visa/work authorization status (e.g., eligible to work in US without sponsorship?)", "answer": "", "category": "personal"},
    {"question": "Marital status", "answer": "", "category": "personal"},
    {"question": "Home address (street, city, state, ZIP/postal code, country)", "answer": "", "category": "personal"},
    {"question": "Phone number (primary and alternate)", "answer": "", "category": "personal"},
    {"question": "Email address", "answer": "", "category": "personal"},
    {"question": "LinkedIn profile URL", "answer": "", "category": "personal"},
    {"question": "Personal website or portfolio URL", "answer": "", "category": "personal"},
    
    # --- CONTACT PREFERENCES ---
    {"question": "Preferred contact method (email, phone, both)", "answer": "", "category": "contact"},
    {"question": "Availability for calls (time zone, best hours)", "answer": "", "category": "contact"},
    {"question": "Willingness to receive marketing emails from the portal", "answer": "No", "category": "contact"},

    # --- EDUCATION HISTORY ---
    {"question": "Highest level of education (high school, associate, bachelor's, master's, PhD, etc.)", "answer": "", "category": "education"},
    {"question": "Degree name (e.g., Bachelor of Science in Computer Science)", "answer": "", "category": "education"},
    {"question": "Field of study / Major / Minor", "answer": "", "category": "education"},
    {"question": "Institution/university name", "answer": "", "category": "education"},
    {"question": "Graduation year (month and year)", "answer": "", "category": "education"},
    {"question": "GPA or percentage (if above a threshold, e.g., 3.0+)", "answer": "", "category": "education"},
    {"question": "Relevant coursework or honors", "answer": "", "category": "education"},
    {"question": "High school details (if no higher education)", "answer": "", "category": "education"},

    # --- WORK EXPERIENCE ---
    {"question": "Job title", "answer": "", "category": "experience"},
    {"question": "Company/employer name", "answer": "", "category": "experience"},
    {"question": "Location (city, state, country)", "answer": "", "category": "experience"},
    {"question": "Start date (month/year)", "answer": "", "category": "experience"},
    {"question": "End date (month/year or 'Present')", "answer": "", "category": "experience"},
    {"question": "Employment type (full-time, part-time, contract, internship, freelance)", "answer": "", "category": "experience"},
    {"question": "Number of direct reports (if managerial)", "answer": "", "category": "experience"},
    {"question": "Key responsibilities (free text or bullet points)", "answer": "", "category": "experience"},
    {"question": "Achievements/accomplishments (quantified, e.g., 'Increased sales by 20%')", "answer": "", "category": "experience"},
    {"question": "Reason for leaving (voluntary, layoff, etc.)", "answer": "", "category": "experience"},
    {"question": "Salary history (current/previous, optional)", "answer": "", "category": "experience"},

    # --- SKILLS AND CERTIFICATIONS ---
    {"question": "Programming languages (e.g., Python, Java)", "answer": "", "category": "skills"},
    {"question": "Tools/software (e.g., Excel, AWS)", "answer": "", "category": "skills"},
    {"question": "Languages spoken (with proficiency: native, fluent, basic)", "answer": "", "category": "skills"},
    {"question": "Certifications (e.g., AWS Certified, PMP) with issue date and provider", "answer": "", "category": "skills"},
    {"question": "Licenses (e.g., driver's license, professional bar admission)", "answer": "", "category": "skills"},

    # --- AVAILABILITY AND LOGISTICS ---
    {"question": "Earliest start date (specific date or notice period)", "answer": "", "category": "logistics"},
    {"question": "Preferred work hours (full-time, part-time)", "answer": "", "category": "logistics"},
    {"question": "Willingness to travel (percentage or yes/no)", "answer": "", "category": "logistics"},
    {"question": "Willingness to relocate (yes/no, to specific locations)", "answer": "", "category": "logistics"},
    {"question": "Remote/hybrid/office preference", "answer": "", "category": "logistics"},
    {"question": "Salary expectations (range, currency)", "answer": "", "category": "logistics"},

    # --- SCREENING / LEGAL ---
    {"question": "Years of experience in [specific field]?", "answer": "", "category": "screening"},
    {"question": "Are you legally authorized to work in [country]?", "answer": "", "category": "screening"},
    {"question": "Do you now or will you require sponsorship?", "answer": "", "category": "screening"},
    {"question": "Have you ever been convicted of a crime? (If yes, explain)", "answer": "No", "category": "screening"},
    {"question": "Why do you want to work here? (200 words max)", "answer": "", "category": "screening"},
    {"question": "Describe a challenge you overcame at work (behavioral)", "answer": "", "category": "screening"},
    {"question": "How many years in current role/industry?", "answer": "", "category": "screening"},
    {"question": "Do you have a valid driver's license?", "answer": "Yes", "category": "screening"},
    {"question": "Availability for shift work/nights/weekends?", "answer": "", "category": "screening"},

    # --- BEHAVIORAL ---
    {"question": "What excites you most about this role/company?", "answer": "", "category": "behavioral"},
    {"question": "Describe your greatest professional achievement and its impact.", "answer": "", "category": "behavioral"},
    {"question": "Tell us about a time you failed and what you learned.", "answer": "", "category": "behavioral"},
    {"question": "How do you prioritize tasks under tight deadlines?", "answer": "", "category": "behavioral"},
    {"question": "Give an example of teamwork leading to success.", "answer": "", "category": "behavioral"},
    {"question": "What feedback have you received that shaped your career?", "answer": "", "category": "behavioral"},
    {"question": "How do you stay updated in your field?", "answer": "", "category": "behavioral"},
    {"question": "Describe handling a difficult customer/colleague.", "answer": "", "category": "behavioral"},
    {"question": "What’s your approach to learning new tools/technologies?", "answer": "", "category": "behavioral"},
    {"question": "Why are you leaving your current job?", "answer": "", "category": "behavioral"},

    # --- SITUATIONAL ---
    {"question": "How would you handle missing a project deadline?", "answer": "", "category": "situational"},
    {"question": "If assigned a task outside your expertise, what next?", "answer": "", "category": "situational"},
    {"question": "Describe improving a process in a past role.", "answer": "", "category": "situational"},
    {"question": "How would you resolve a team conflict?", "answer": "", "category": "situational"},
    {"question": "What would you do if given unclear instructions?", "answer": "", "category": "situational"},
    {"question": "How do you manage multiple competing projects?", "answer": "", "category": "situational"},
    {"question": "If you disagreed with a manager’s decision, how would you proceed?", "answer": "", "category": "situational"},
    {"question": "Explain adapting to major workplace changes.", "answer": "", "category": "situational"},
    {"question": "How would you contribute to diversity/inclusion here?", "answer": "", "category": "situational"},
    {"question": "What’s your strategy for the first 90 days in this role?", "answer": "", "category": "situational"},

    # --- COMPLIANCE ---
    {"question": "Are you a protected veteran (yes/no)?", "answer": "", "category": "compliance"},
    {"question": "Do you have a disability (yes/no, optional)?", "answer": "", "category": "compliance"},
    {"question": "Identify your ethnicity/race (multi-select, optional)?", "answer": "", "category": "compliance"},
    {"question": "Pronouns (he/him, she/her, they/them)?", "answer": "", "category": "compliance"},
    {"question": "Sexual orientation (optional, for DEI tracking)?", "answer": "", "category": "compliance"},
    {"question": "How did you hear about this job? (dropdown: portal, referral, etc.)", "answer": "", "category": "compliance"},

     # --- CREATIVE ---
    {"question": "What’s your superpower?", "answer": "", "category": "creative"},
    {"question": "Share a fun fact about yourself.", "answer": "", "category": "creative"},
    {"question": "Favorite book/podcast influencing your work?", "answer": "", "category": "creative"},
    {"question": "If not your career, what path would you pursue?", "answer": "", "category": "creative"},
    {"question": "Send your favorite meme/GIF.", "answer": "", "category": "creative"},
    {"question": "Describe your work style in three adjectives.", "answer": "", "category": "creative"},
    {"question": "What’s an unusual hobby/skill you have?", "answer": "", "category": "creative"}
]

def seed_user_questions(user_id):
    """
    Seeds the default smart answers for a specific user.
    """
    try:
        db = SessionLocal()
        
        # 1. Bulk Select Existing Questions
        existing_qs = db.query(QuestionAnswer.question).filter_by(user_id=user_id).all()
        existing_set = {r[0] for r in existing_qs}
        
        # 2. Filter New Questions
        new_records = []
        for q in DEFAULT_SMART_ANSWERS:
            if q['question'] not in existing_set:
                new_records.append(QuestionAnswer(
                    user_id=user_id,
                    question=q['question'],
                    answer=q['answer'],
                    category=q['category']
                ))
        
        # 3. Bulk Insert
        if new_records:
            db.bulk_save_objects(new_records)
            db.commit()
            return True, f"Seeded {len(new_records)} new questions."
            
        db.close()
        return True, "Questions already up to date."
    except Exception as e:
        logger.error(f"Seeding failed for user {user_id}: {e}")
        return False, str(e)



def seed_admin():
    """
    Ensures the default admin user exists and has the correct password.
    """
    try:
        db = SessionLocal()
        # Changed to .tech as per user preference (Permanent Admin)
        admin_email = "admin@hirelink.tech"
        admin = db.query(AppUser).filter_by(email=admin_email).first()
        
        if not admin:
            logger.info("Seeding Admin User...")
            admin = AppUser(
                name="System Admin", 
                email=admin_email, 
                is_admin=True, 
                is_onboarded=True,
                subscription_plan="PRO_PLUS"
            )
            admin.set_password("admin123") # Slightly stronger default default
            db.add(admin)
            db.commit() # Commit to get ID
            
            # Seed Questions for Admin specifically
            seed_user_questions(admin.id)
        else:
            # Force update permissions and password
            admin.is_admin = True
            admin.set_password("admin123") # Standardize default
            admin.subscription_plan = "PRO_PLUS"
            logger.info("Updated Admin permissions and password.")
            db.commit()
            
            # Ensure Admin has questions even if existing
            seed_user_questions(admin.id)
            
        db.close()
    except Exception as e:
        logger.error(f"Failed to seed admin: {e}")

def init_db():
    logger.info(f"Initializing database at {DB_PATH}")
    migrate_db() # Run migration checks before create_all
    Base.metadata.create_all(bind=engine)
    seed_admin() # Ensure admin exists
    
    # NOTE: REMOVED GLOBAL DEFAULT QUESTION SEEDING
    # It was causing performance issues (loading all Qs) and created orphaned rows (user_id=None).
    # Questions are now seeded per-user via seed_user_questions().
            
    logger.info("Database initialized successfully.")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

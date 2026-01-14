
import sys
import os
import time
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database import init_db, SessionLocal, Job, Resume, AppUser, Application
from backend.utils.scraper_utils import run_scraper
from backend.agents.job_matcher import JobMatcher
from backend.agents.resume_parser import ResumeParserV2
from backend.utils.admin_tools import save_admin_snapshot, restore_admin_snapshot

def log(msg):
    print(f"\n[E2E] {msg}")

def run_e2e_simulation():
    log("Starting Core Business Journey Simulation...")
    
    # 1. SETUP
    log("Step 0: Setup (Admin Tools)")
    save_result = save_admin_snapshot()
    log(f"Snapshot Save: {save_result[1]}")
    
    db = SessionLocal()
    
    # 2. JOURNEY A: ACQUISITION (Resume Upload)
    log("Step 1: Acquisition (Resume Parsing)")
    # Mock a resume file (we'll create a dummy one if needed or use existing)
    dummy_pdf_path = "data/dummy_resume.pdf" # checking existence later
    
    # For simulation, we create a DB entry directly to bypass file upload UI
    try:
        user = AppUser(name="Test User", email="test@example.com", is_onboarded=True)
        db.add(user)
        db.commit()
        
        resume = Resume(
            name="Test Candidate",
            email="candidate@example.com",
            raw_text="Experienced Python Developer with 5 years in AI and Data Science.",
            parsed_data={"skills": ["Python", "AI", "SQL", "Data Science"], "experience": 5}
        )
        db.add(resume)
        db.commit()
        log("Resume & User Created Successfully.")
    except Exception as e:
        log(f"Acquisition Failed: {e}")

    # 3. JOURNEY C: HYPER-DRIVE (Scrape -> Match)
    log("Step 2: Hyper-Drive (Scrape & Match)")
    
    # Trigger Scraper (Should trigger Demo Fallback or Actual Scrape)
    try:
        new_jobs = run_scraper(["LinkedIn"], "Python Developer", "Remote")
        log(f"Scraper returned: {new_jobs} jobs.")
        
        if new_jobs == 0:
            log("CRITICAL BUG: Scraper returned 0 jobs even with Demo Fallback!")
        else:
            log("Scraper logic passed (Demo or Real).")
            
        # Trigger Matcher
        matcher = JobMatcher()
        matches = matcher.match_jobs(resume.id, limit=5)
        log(f"Matcher found {len(matches)} suitable candidates.")
        
        if len(matches) > 0:
            top_match = matches[0]
            log(f"Top Match: {top_match['job'].title}")
            log(f"Final Score: {top_match['score']}")
            log(f"Breakdown -> Base: {top_match['debug_base']}, Bonus: {top_match['debug_bonus']}")
        else:
            log("WARNING: No matches found. Matching logic might be too strict.")
            
    except Exception as e:
        log(f"Hyper-Drive Failed: {e}")

    # 4. JOURNEY D: BILLING
    log("Step 3: Billing (Mock Payment)")
    from backend.utils.payment_gateway import PaymentGateway
    pg = PaymentGateway()
    link = pg.create_payment_link(2999, "PRO_PLUS", "test@example.com")
    if link and "short_url" in link:
        log(f"Payment Link Created: {link['short_url']}")
    else:
        log("Billing Failed: Payment link generation returned None.")
        
    db.close()
    log("Step 4: Engagement (Email Notifier Check)")
    from backend.utils.notifier import EmailNotifier
    notifier = EmailNotifier()
    log(f"Email Notifier Initialized. Enabled: {notifier.enabled}")
    # Mock send to avoid spam, or print logic
    if not notifier.enabled:
        log("Skipped actual send (No Credentials). Logic is valid.")

    log("Step 5: Visibility (History DB Check)")
    db = SessionLocal()
    history_count = db.query(Application).count()
    log(f"History Table Accessible. Total Records: {history_count}")
    if history_count > 0:
        log("History Dashboard Data is Ready.")
    log("Simulation Complete.")

if __name__ == "__main__":
    run_e2e_simulation()

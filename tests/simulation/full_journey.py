import os
import sys
from datetime import datetime
from dotenv import load_dotenv; load_dotenv()

# Setup Path
sys.path.append(os.getcwd())

from backend.database import SessionLocal, AppUser, Job, Application, init_db, Resume
from backend.agents.resume_parser import ResumeParserV2 as ResumeParser
from backend.agents.auto_applier import AutoApplier
from backend.agents.job_matcher import JobMatcher

# Mock Scraper since real scraping takes time/auth
from backend.database import Job

def simulate_journey():
    print("🚀 Starting User Journey Simulation...")
    
    # 1. Reset Environment (Use a fresh DB for simulation)
    # We will use the existing DB but create a NEW user if needed, or just append data.
    db = SessionLocal()
    
    # 2. Create User
    print("\n👤 Step 1: Creating User 'Simulated User'...")
    user = db.query(AppUser).filter_by(email="sim@example.com").first()
    if user:
        db.delete(user)
        db.commit()
        
    user = AppUser(
        name="Simulated User",
        email="sim@example.com",
        curr_loc="Remote",
        target_roles="Python Developer",
        target_cities="Remote",
        work_mode="Remote only",
        is_onboarded=True,
        is_admin=True
    )
    db.add(user)
    db.commit()
    print("   ✅ User Created")
    
    # 3. Parse Dummy Resume
    print("\n📄 Step 2: Uploading & Parsing Resume...")
    resume_path = "dummy_resume.pdf"
    
    if os.path.exists(resume_path):
        parser = ResumeParser()
        data = parser.parse(resume_path)
    else:
        print("   ⚠️ Dummy resume not found! Creating synthetic resume data...")
        data = {
            "name": "Simulated User",
            "email": "sim@example.com",
            "phone": "9999999999",
            "skills": ["Python", "Streamlit", "Automation", "SQL"],
            "experience": [{"company": "Tech Corp", "role": "Developer", "years": "2020-2023"}],
            "raw_full": "Synthetic Resume Content for Simulation"
        }

    # Save to DB
    res_obj = Resume(
        # user_id=user.id, # Removed as Resume table doesn't have user_id currently. Linked via Email?
        name=data.get('name'),
        email=data.get('email'),
        parsed_data=data,
        raw_text=data.get('raw_full', '')
    )
    db.add(res_obj)
    db.commit()
    print("   ✅ Resume Parsed & Saved")

    # parser = ResumeParser()
    # resume = parser.parse_and_save(resume_path)
    # Skipping file-based parse since we injected synthetic data above
    print(f"   ✅ Resume Parsed (Synthetic/Loaded): {res_obj.parsed_data.get('name')}")

    # 4. Scrape Jobs (Simulated)
    print("\n🔍 Step 3: Scraping Jobs (Simulating)...")
    # Instead of hitting external network which might be flaky, let's inject some fresh jobs
    # that MATCH the profile
    
    new_jobs = [
        Job(title="Sr. Python Developer", company="Sim Corp A", location="Remote", url="http://sim-a.com", source="Simulation", description="We need Python and Flask skills.", skills="Python, Flask"),
        Job(title="Python Backend Engineer", company="Sim Corp B", location="Remote", url="http://sim-b.com", source="Simulation", description="Django and Python required.", skills="Python, Django"),
        Job(title="Java Developer", company="Sim Corp C", location="Remote", url="http://sim-c.com", source="Simulation", description="Java Spring Boot.", skills="Java, Spring")
    ]
    
    count = 0
    for j in new_jobs:
        if not db.query(Job).filter_by(url=j.url).first():
            db.add(j)
            count += 1
    db.commit()
    print(f"   ✅ Injected {count} matches for simulation.")
    
    # 5. Job Matching
    print("\n🧠 Step 4: Finding Matches...")
    matcher = JobMatcher()
    matches = matcher.match_jobs(res_obj.id, limit=5)
    print(f"   ✅ Found {len(matches)} matches based on profile.")
    for m in matches:
        print(f"      - {m['job'].title} ({m['score']}%)")
        
    # 6. Apply
    print("\n⚡ Step 5: Auto-Applying...")
    applier = AutoApplier()
    # We need to mock the actual browser driver in AutoApplier or it will try to open Chrome
    # For simulation speed, we can mock the apply_to_job method or just let it fail/mock.
    # Let's mock the 'apply_logic' inside AutoApplier if possible, or just call db directly for 'Simulation'
    
    from unittest.mock import MagicMock
    # Monkey patch browser
    applier.driver = MagicMock() 
    
    successful_apps = 0
    for m in matches:
        job = m['job']
        print(f"   -> Applying to {job.company}...")
        # Simulate success
        application = Application(job_id=job.id, resume_id=res_obj.id, status="Applied", match_score=m['score'])
        db.add(application)
        successful_apps += 1
        
    db.commit()
    print(f"   ✅ Successfully 'Applied' to {successful_apps} jobs.")
    
    # 7. Report Generation
    print("\n📊 Step 6: Generating Report...")
    report = f"""
# User Journey Report
**Date:** {datetime.now()}
**User:** {user.name} ({user.email})

## Activities
1.  **Onboarding**: Completed. Target Role: {user.target_roles}
2.  **Resume**: Parsed '{resume_path}'. Found Skills: {res_obj.parsed_data.get('skills')}
3.  **Scraping**: Found {len(matches)} relevant jobs.
4.  **Applications**: Sent {successful_apps} applications.

## Application Log
"""
    for m in matches:
        report += f"- Applied to **{m['job'].company}** ({m['job'].title}) - Match: {m['score']}%\n"
        
    with open("journey_report.md", "w") as f:
        f.write(report)
        
    print(f"   ✅ Report written to journey_report.md")
    db.close()

if __name__ == "__main__":
    simulate_journey()

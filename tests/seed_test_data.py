
import sys
import os
import random
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database import SessionLocal, init_db, AppUser, Resume, Job, QuestionAnswer, PortalCredential

def seed_test_data():
    print("--- SEEDING TEST DATA ---")
    db = SessionLocal()
    
    try:
        # 1. Clean Slate (Optional: Be careful in prod)
        # db.query(AppUser).delete()
        # db.query(Job).delete()
        # db.query(Resume).delete()
        # db.commit()

        # 2. Create Users
        users = [
            {
                "email": "admin@hirelink.tech", "name": "System Admin", 
                "plan": "PRO_PLUS", "is_admin": True, "password": "admin123"
            },
            {
                "email": "new.user@example.com", "name": "Newbie User", 
                "plan": "TRIAL", "is_admin": False, "password": "user123"
            },
            {
                "email": "pro.user@example.com", "name": "Professional User", 
                "plan": "PRO", "is_admin": False, "password": "user123"
            }
        ]

        created_users = {}

        for u_data in users:
            existing = db.query(AppUser).filter_by(email=u_data['email']).first()
            if not existing:
                user = AppUser(
                    email=u_data['email'],
                    name=u_data['name'],
                    subscription_plan=u_data['plan'],
                    is_admin=u_data['is_admin'],
                    is_onboarded=True
                )
                user.set_password(u_data['password'])
                
                # Add dummy preferences
                user.target_roles = "Python Developer, Backend Engineer"
                user.target_cities = "Remote, Bangalore, San Francisco"
                user.work_mode = "Remote"
                
                db.add(user)
                db.commit()
                created_users[u_data['email']] = user
                print(f"Created User: {u_data['email']}")
            else:
                created_users[u_data['email']] = existing
                print(f"User already exists: {u_data['email']}")

        # 3. Create Resumes (Linked to Users ideally, but schema might be loose currently)
        # We will link resume to Pro User for the flow
        pro_user = created_users["pro.user@example.com"]
        
        existing_resume = db.query(Resume).filter_by(email=pro_user.email).first()
        if not existing_resume:
            resume = Resume(
                name=pro_user.name,
                email=pro_user.email,
                phone="123-456-7890",
                raw_text="Experienced Python Developer with expertise in Flask, Django, and AI agents. 5 years of experience.",
                parsed_data={
                    "name": pro_user.name,
                    "email": pro_user.email,
                    "skills": ["Python", "Flask", "SQLAlchemy", "Selenium", "Docker"],
                    "experience": [
                        {
                            "role": "Senior Python Dev",
                            "company": "Tech Corp",
                            "years": 3,
                            "description": "Built scalable APIs and AI bots."
                        }
                    ],
                    "contact": {
                        "name": pro_user.name,
                        "email": pro_user.email,
                        "phone": "123-456-7890"
                    }
                }
            )
            db.add(resume)
            db.commit() # Get ID
            print(f"Created Resume for {pro_user.email} (ID: {resume.id})")
        
            # Link this resume ID to something if needed? 
            # In current schema, Application links them.
        else:
             print(f"Resume already exists for {pro_user.email}")
             resume = existing_resume

        # 4. Create Mock Jobs
        titles = ["Python Developer", "Backend Engineer", "AI Specialist", "Full Stack Dev"]
        sources = ["LinkedIn", "Indeed", "Naukri"]
        
        for i in range(10):
            job_title = random.choice(titles)
            source = random.choice(sources)
            unique_url = f"https://mock-portal.com/job/{random.randint(1000, 9999)}"
            
            existing_job = db.query(Job).filter_by(url=unique_url).first()
            if not existing_job:
                job = Job(
                    title=job_title,
                    company=f"Mock Company {i}",
                    location="Remote",
                    salary="$100k - $150k",
                    description="We are looking for a skilled Python developer to join our team. Must know AI and SQL.",
                    skills="Python, SQL, AI",
                    url=unique_url,
                    source=source,
                    posted_date=datetime.utcnow() - timedelta(days=random.randint(0, 5)),
                    is_easy_apply=random.choice([True, False])
                )
                db.add(job)
        
        db.commit()
        print("Created 10 Mock Jobs.")

        # 5. Create Portal Credentials (Safe Mock)
        mock_creds = {
            "LinkedIn": {"user": "mock_linkedin_user", "pass": "mock_pass"},
            "Indeed": {"user": "mock_indeed_user", "pass": "mock_pass"}
        }
        
        for portal, creds in mock_creds.items():
            existing = db.query(PortalCredential).filter_by(user_id=pro_user.id, portal_name=portal).first()
            if not existing:
                pc = PortalCredential(
                    user_id=pro_user.id,
                    portal_name=portal,
                    username=creds['user'],
                    password=creds['pass']
                )
                db.add(pc)
        db.commit()
        print("Created Mock Credentials.")

    except Exception as e:
        print(f"Seeding Failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_test_data()

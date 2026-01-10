
import json
from datetime import datetime
from backend.database import SessionLocal, AppUser, Resume, QuestionAnswer, Application

def export_user_data_json(user_id=1):
    """
    Aggregates all critical user data into a portable JSON structure.
    """
    db = SessionLocal()
    data = {
        "export_date": datetime.utcnow().isoformat(),
        "user_profile": {},
        "smart_answers": [],
        "resume_data": {},
        "applications": []
    }
    
    try:
        # 1. User Profile
        user = db.query(AppUser).filter_by(id=user_id).first()
        if user:
            data["user_profile"] = {
                "name": user.name,
                "email": user.email,
                "linkedin": user.linkedin,
                "portfolio": user.website,
                "target_roles": user.target_roles,
                "preferences": {
                    "locations": user.target_cities,
                    "work_mode": user.work_mode
                }
            }
            
        # 2. Smart Answers (The most painful thing to re-enter)
        answers = db.query(QuestionAnswer).filter(QuestionAnswer.answer != "").all()
        for a in answers:
            data["smart_answers"].append({
                "question": a.question,
                "answer": a.answer,
                "category": a.category
            })
            
        # 3. Resume Data (Latest)
        resume = db.query(Resume).order_by(Resume.id.desc()).first()
        if resume:
            data["resume_data"] = {
                "filename": resume.name, # basic info
                "parsed_skills": resume.parsed_data.get('skills', []) if resume.parsed_data else [],
                "raw_text_preview": resume.raw_text[:200] if resume.raw_text else ""
            }
            
        # 4. Application History
        apps = db.query(Application).all()
        data["applications"] = [
            {"job_id": app.job_id, "status": app.status, "date": str(app.applied_at)} 
            for app in apps
        ]
        
        return json.dumps(data, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)})
    finally:
        db.close()

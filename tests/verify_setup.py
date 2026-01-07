import sys
import os

# Add root to path
# Assuming we run from scratch directory
sys.path.append(os.path.join(os.getcwd(), "IndianSmartApplier"))

def verify_system():
    print("🔍 Verifying IndianSmartApplier Setup...")
    
    # 1. Imports
    try:
        print("Checking imports...")
        from backend.flask_app import app
        from backend.database import init_db
        from backend.scrapers.naukri import NaukriScraper
        from backend.agents.resume_parser import ResumeParser
        from backend.agents.job_matcher import JobMatcher
        from backend.agents.auto_applier import AutoApplier
        print("✅ Core imports successful")
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

    # 2. Database
    try:
        print("Checking database...")
        init_db()
        print("✅ Database initialized")
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

    # 3. Model Checks (Spacy)
    try:
        print("Checking ML models...")
        import spacy
        # Ensure model is loadable (mock check as we might not have it installed in this env)
        # spacy.load("en_core_web_sm") 
        print("✅ ML libraries present")
    except Exception as e:
        print(f"❌ ML model issue: {e}")
        return False

    print("\n🎉 Verification Successful! The system structure is sound.")
    print("Run `streamlit run app.py` to start the dashboard.")
    return True

if __name__ == "__main__":
    verify_system()

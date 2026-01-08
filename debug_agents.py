from backend.agents.cover_letter_generator import CoverLetterGenerator
from backend.agents.job_analyzer import JobAnalyzer
import os

def test_agents():
    print("="*30)
    print("Testing Intelligent Agents")
    print("="*30)
    
    key = os.getenv("GEMINI_API_KEY")
    has_key = bool(key)
    print(f"LLM Key Present: {has_key}")

    # --- MOCK DATA ---
    mock_resume = """
    Sandeep Kashyap
    Senior Python Developer with 5 years experience in Flask, Django, SQL.
    AWS Certified Solutions Architect.
    """
    
    mock_jd = """
    Job Title: Senior Backend Engineer
    Company: TechCorp
    Requirements:
    - 4+ years in Python (Flask/Django)
    - Experience with AWS and Docker
    - Knowledge of Kubernetes is a plus
    - Strong SQL skills
    """
    
    skills = ["Python", "Flask", "AWS", "SQL"]

    # 1. Test Cover Letter
    print("\n--- 1. Testing Cover Letter Gen ---")
    gen = CoverLetterGenerator()
    letter = gen.generate("Senior Backend Engineer", "TechCorp", "Sandeep", skills, mock_resume)
    print("Generated Letter Preview:")
    print(letter[:200] + "..." if letter else "None")
    
    if "Hiring Manager" in letter and not has_key:
        print("✅ Correctly used template fallback.")
    elif has_key and len(letter) > 50:
        print("✅ LLM Generation likely successful.")

    # 2. Test Job Analyzer
    print("\n--- 2. Testing Job Analyzer ---")
    analyzer = JobAnalyzer()
    
    if has_key:
        print("Running Analysis...")
        result = analyzer.analyze_suitability(mock_jd, mock_resume)
        if result:
            print("Analysis Result:")
            import json
            print(json.dumps(result, indent=2))
        else:
            print("❌ Analysis failed (returned None).")
    else:
        print("⚠️ No API Key. Skipping Job Analyzer test (requires LLM).")

if __name__ == "__main__":
    test_agents()

from backend.agents.resume_parser import ResumeParser
import os

def test_parser():
    print("="*30)
    print("Testing Resume Parser (LLM Upgrade)")
    print("="*30)
    
    # Check for API Key
    key = os.getenv("GEMINI_API_KEY")
    if key:
        print(f"✅ GEMINI_API_KEY found: {key[:5]}...****")
    else:
        print("⚠️ GEMINI_API_KEY NOT found. Expecting Fallback to Regex.")

    parser = ResumeParser()
    
    # 1. Mock Text (instead of PDF for speed)
    mock_resume_text = """
    Sandeep Kashyap
    Email: sandeep@example.com
    Phone: +91-9876543210
    
    Summary
    Senior Python Developer with 5 years of experience building scalable backends using Flask and Django.
    
    Experience
    Senior Software Engineer | TechCorp | 2020 - Present
    - Built a resume parser using Gemini.
    - Optimized SQL queries reducing latency by 30%.
    
    Education
    B.Tech Computer Science | IISc Bangalore | 2016 - 2020
    
    Skills: Python, SQL, AWS, Docker, Kubernetes, React
    """
    
    print("\n--- 1. Testing LLM Extraction (Mock Text) ---")
    try:
        # Direct call to internal method for testing
        if parser.llm_client.client:
            print("Invoking LLM...")
            result = parser.extract_with_llm(mock_resume_text)
            print("LLM Result JSON:")
            import json
            print(json.dumps(result, indent=2))
        else:
            print("LLM Client not active (no key). Skipping direct LLM test.")
    except Exception as e:
        print(f"LLM Test Failed: {e}")

    print("\n--- 2. Testing Full Parse Flow (Fallback Check) ---")
    # mimicking parse_and_save but without actual file read
    data = {}
    
    # Try LLM
    if parser.llm_client.client:
        llm_data = parser.extract_with_llm(mock_resume_text)
        if llm_data:
            data = llm_data
            
    # Fallback
    if not data.get('email'): 
        data['email'] = parser.extract_email(mock_resume_text)
        print("Fallback Email triggered")
    if not data.get('phone'): 
        data['phone'] = parser.extract_phone(mock_resume_text)
        print("Fallback Phone triggered")
        
    print("\nFinal Merged Data:")
    import json
    print(json.dumps(data, indent=2))

if __name__ == "__main__":
    test_parser()

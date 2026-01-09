from backend.agents.resume_parser import ResumeParser, SimpleResume
import spacy

def test_extract_name_jira():
    parser = ResumeParser()
    
    # Text that previously failed
    text = """
    Jira
    Project Management Tool
    
    Sandeep Ramaswamy Kashyap
    Python Developer
    """
    
    name = parser.extract_name(text)
    print(f"Extracted Name: '{name}'")
    
    if name == "Jira":
        print("❌ FAILED: Extracted 'Jira'")
    elif name == "Sandeep Ramaswamy Kashyap":
        print("✅ PASSED: Extracted correct name")
    else:
        print(f"⚠️  Result: '{name}' (Expected 'Sandeep Ramaswamy Kashyap')")

if __name__ == "__main__":
    test_extract_name_jira()

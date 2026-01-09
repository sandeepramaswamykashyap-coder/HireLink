from unittest.mock import MagicMock, patch
import pytest
from backend.agents.resume_parser import ResumeParser, SimpleResume

@pytest.fixture
def parser():
    # Mock spacy load to prevent slow loading / startup in tests
    with patch('spacy.load') as mock_load:
        mock_nlp = MagicMock()
        mock_load.return_value = mock_nlp
        yield ResumeParser()

def test_extract_email_regex(parser):
    text = "Contact: test.user@example.com"
    email = parser.extract_email(text)
    assert email == "test.user@example.com"

def test_extract_phone_regex(parser):
    text = "Call me at +91 9876543210"
    phone = parser.extract_phone(text)
    assert phone == "+91 9876543210"

def test_extract_skills(parser):
    text = "I know Python, Java and SQL."
    skills = parser.extract_skills(text)
    assert "Python" in skills
    assert "Java" in skills
    assert "SQL" in skills

@patch('backend.agents.resume_parser.Resume')
@patch('backend.database.SessionLocal') # Patch the source since it is imported locally
@patch('backend.utils.llm_client.LLMClient')
def test_parse_and_save_mock_llm(MockLLM, MockSession, MockResume, parser):
    # Mock LLM response
    mock_llm_instance = MockLLM.return_value
    mock_llm_instance.client = True 
    mock_llm_instance.generate_json.return_value = {
        "name": "Jane Doe",
        "email": "jane@example.com",
        "skills": ["C++", "Rust"]
    }
    
    # Inject Mock into Parser instance
    parser.llm_client = mock_llm_instance
    
    # Mock Database
    mock_db = MockSession.return_value
    
    # Mock ORM Object creation
    mock_resume_obj = MagicMock()
    mock_resume_obj.id = 123
    MockResume.return_value = mock_resume_obj
    
    # Mock extract_text to return string
    with patch.object(parser, 'extract_text', return_value="Resume text content"):
         result = parser.parse_and_save("dummy.pdf")
         
         # Verification
         assert result.id == 123
         assert result.parsed_data["name"] == "Jane Doe"
         assert result.parsed_data["email"] == "jane@example.com"
         
         # Verify DB calls
         mock_db.add.assert_called()
         mock_db.commit.assert_called()

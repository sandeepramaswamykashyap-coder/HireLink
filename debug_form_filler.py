from backend.agents.llm_form_filler import LLMFormFiller
from unittest.mock import MagicMock
import json
import os

def test_llm_filler():
    print("="*30)
    print("Testing LLM Form Filler")
    print("="*30)
    
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        print("⚠️ No API Key found. Proceeding with MOCK verify.")
        # return  <-- Removed


    # 1. Mock Driver & Elements
    print("1. Setting up Mock Driver...")
    mock_driver = MagicMock()
    
    # Mock finding elements
    # We will simulate a simple form: Name, Email, "Why should we hire you?"
    mock_input_name = MagicMock()
    mock_input_name.is_displayed.return_value = True
    mock_input_name.get_attribute.side_effect = lambda x: "text" if x=="type" else "name" if x=="name" else "full_name" if x=="id" else ""
    
    mock_input_email = MagicMock()
    mock_input_email.is_displayed.return_value = True
    mock_input_email.get_attribute.side_effect = lambda x: "email" if x=="type" else "email" if x=="name" else "email_id" if x=="id" else ""
    
    mock_input_why = MagicMock() # Representing a text input for simplified test
    mock_input_why.is_displayed.return_value = True
    mock_input_why.get_attribute.side_effect = lambda x: "text" if x=="type" else "reason" if x=="name" else "why_hire" if x=="id" else ""

    mock_driver.find_elements.side_effect = lambda by, val: [mock_input_name, mock_input_email, mock_input_why] if val == "input" else []

    # Mock User Profile
    user_profile = {
        "name": "Sandeep Kashyap",
        "email": "test@example.com",
        "skills": ["Python", "AI"],
        "experience": "5 Years"
    }

    # 2. Instantiate Filler
    filler = LLMFormFiller(mock_driver)
    
    # 3. Test Extraction (Mocked)
    print("2. Testing Context Extraction...")
    # Injecting our mock find_element behavior for labels
    def find_label(selector):
        lbl = MagicMock()
        if "full_name" in selector: lbl.text = "Full Name"
        elif "email_id" in selector: lbl.text = "Email Address"
        elif "why_hire" in selector: lbl.text = "Why should we hire you?"
        return lbl
    mock_driver.find_element.side_effect = lambda by, val: find_label(val)
    
    elements = filler.extract_form_context()
    print(f"Extracted {len(elements)} elements.")
    print(json.dumps(elements, indent=2))
    
    # 4. Test Execution with Mocked LLM Response
    print("\n3. Testing Execution Logic (Mocked LLM)...")
    
    # Simulate LLM Response
    mock_actions = {
        "input_0": "Sandeep Kashyap",
        "input_1": "test@example.com",
        "input_2": "Because I am an expert agent."
    }
    
    if key:
        print("API Key present, attempting real LLM call...")
        real_actions = filler.determine_actions(elements, user_profile)
        if real_actions: mock_actions = real_actions
    else:
        print("No API Key. Using Mock LLM Response for execution test.")

    print("Decided Actions:")
    print(json.dumps(mock_actions, indent=2))
    
    # Inject Mock Decision into Filler (A bit hacky, but we are testing fill_form logic)
    # We will manually invoke fill_form's valid parts or just verify fill_form calls
    
    # Let's mock the determine_actions method to return our actions
    filler.determine_actions = MagicMock(return_value=mock_actions)
    
    print("\n4. Running fill_form()...")
    # We need to reset mock_driver find_elements to return elements again for the execute phase
    mock_driver.find_elements.side_effect = lambda by, val: [mock_input_name, mock_input_email, mock_input_why] if val == "input" else []
    
    success = filler.fill_form(user_profile)
    
    if success:
        print("✅ fill_form() returned True")
        # Verify calls
        mock_input_name.send_keys.assert_called_with("Sandeep Kashyap")
        print("✅ Name filled.")
        mock_input_email.send_keys.assert_called_with("test@example.com")
        print("✅ Email filled.")
    else:
        print("❌ fill_form() failed.")

if __name__ == "__main__":
    test_llm_filler()

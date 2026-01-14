import sys
import os
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.getcwd())

from backend.utils.llm_client import LLMClient
from backend.utils.logger import logger

def test_llm():
    print("Testing LLM Connectivity with gemini-2.0-flash...")
    client = LLMClient()
    
    if not client.client:
        print("❌ LLM Client failed to initialize.")
        return

    prompt = "Return a JSON object with a 'status' field saying 'connected' and 'message' field saying 'test successful'."
    response = client.generate_json(prompt)
    
    if response and response.get("status") == "connected":
        print(f"✅ LLM Connectivity Test Successful: {response}")
    else:
        print(f"❌ LLM Connectivity Test Failed. Response: {response}")

if __name__ == "__main__":
    load_dotenv()
    test_llm()

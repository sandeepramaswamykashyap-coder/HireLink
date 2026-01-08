import google.generativeai as genai
import os

key = os.getenv("GEMINI_API_KEY")
if not key:
    print("No API Key found")
else:
    genai.configure(api_key=key)
    try:
        print("Listing Models:")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(m.name)
    except Exception as e:
        print(f"Error: {e}")

import os
from backend.utils.logger import logger

class LLMClient:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = None
        self._setup_client()

    def _setup_client(self):
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not found in environment variables. LLM features will be disabled.")
            return

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel('gemini-1.5-flash')
            logger.info("LLM Client (Gemini 1.5 Flash) initialized successfully.")
        except ImportError:
            logger.error("google-generativeai library not installed.")
        except Exception as e:
            logger.error(f"Failed to initialize LLM Client: {e}")

    def generate_json(self, prompt):
        """
        Generate JSON output from the LLM.
        """
        if not self.client:
            logger.warning("LLM Client not initialized. Returning None.")
            return None

        try:
            # Enforce JSON structure in prompt if not present, but Gemini Pro often needs clear instruction
            full_prompt = f"{prompt}\n\nIMPORTANT: Return ONLY valid JSON. No markdown formatting, no code blocks."
            
            response = self.client.generate_content(full_prompt)
            text = response.text
            
            # Clean up potential markdown code blocks
            clean_text = text.replace("```json", "").replace("```", "").strip()
            
            import json
            return json.loads(clean_text)
            
        except Exception as e:
            logger.error(f"LLM Generation Error: {e}")
            return None

    def generate_text(self, prompt):
        """
        Generate plain text output.
        """
        if not self.client:
            return None
            
        try:
            response = self.client.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"LLM Text Generation Error: {e}")
            return None

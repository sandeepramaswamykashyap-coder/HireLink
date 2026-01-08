from backend.utils.llm_client import LLMClient
from backend.utils.logger import logger
import json

class JobAnalyzer:
    def __init__(self):
        self.llm_client = LLMClient()

    def analyze_suitability(self, job_description, resume_text):
        """
        Analyze the fit between a job description and a resume.
        Returns a JSON object with score and reasoning.
        """
        if not self.llm_client.client or not job_description or not resume_text:
            return None

        try:
            prompt = f"""
            You are an expert Job Suitability Analyzer (Recruiter AI). 
            Compare the Job Description (JD) and Candidate Resume below.
            
            Determine a match score (0-100) and provide reasons.
            
            RETURN JSON ONLY using this schema:
            {{
                "score": int, (0-100)
                "match_reason": "Summary of why this is a good match",
                "missing_skills": ["List of critical skills in JD but missing in Resume"],
                "keywords_to_add": ["Keywords the candidate should add to resume to improve ATS score"]
            }}

            --- JOB DESCRIPTION ---
            {job_description[:3000]}
            
            --- RESUME ---
            {resume_text[:3000]}
            """
            
            analysis = self.llm_client.generate_json(prompt)
            if analysis:
                return analysis
            
        except Exception as e:
            logger.error(f"Job Analysis failed: {e}")
            
        return None

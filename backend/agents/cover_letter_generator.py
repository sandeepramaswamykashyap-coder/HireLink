import random
from backend.utils.llm_client import LLMClient
from backend.utils.logger import logger

class CoverLetterGenerator:
    def __init__(self):
        self.llm_client = LLMClient()

    def generate(self, job_title, company_name, candidate_name, skills, resume_text=None):
        """
        Generate a cover letter. Tries LLM first, falls back to templates.
        """
        # 1. Try LLM Generation
        if self.llm_client.client:
            try:
                logger.info(f"Generating AI cover letter for {company_name}")
                prompt = f"""
                Write a professional and persuasive cover letter for the following role.
                
                Candidate: {candidate_name}
                Role: {job_title}
                Company: {company_name}
                Key Skills: {', '.join(skills) if isinstance(skills, list) else skills}
                
                Resume Context:
                {resume_text[:2000] if resume_text else "No specific resume text provided."}
                
                Instructions:
                - Keep it concise (under 250 words).
                - Highlight why the candidate is a good fit based on the skills.
                - Use a professional but enthusiastic tone.
                - structured as standard cover letter (Dear Hiring Manager...)
                """
                
                letter = self.llm_client.generate_text(prompt)
                if letter:
                    return letter.strip()
            except Exception as e:
                logger.error(f"LLM Cover Letter Gen failed: {e}")
        
        # 2. Template Fallback
        logger.info("Using template fallback for cover letter.")
        skills_str = ', '.join(skills[:3]) if isinstance(skills, list) else str(skills)
        templates = [
            f"Dear Hiring Manager,\n\nI am writing to express my strong interest in the {job_title} position at {company_name}. With my experience in {skills_str}, I believe I can contribute significantly to your team.\n\nSincerely,\n{candidate_name}",
            f"To the Recruitment Team at {company_name},\n\nI am excited to apply for the {job_title} role. My background in {skills_str} aligns perfectly with your requirements.\n\nBest regards,\n{candidate_name}"
        ]
        return random.choice(templates)

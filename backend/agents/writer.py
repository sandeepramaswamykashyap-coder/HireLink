import os
from fpdf import FPDF
import google.generativeai as genai
from backend.utils.logger import logger
from datetime import datetime

class CoverLetterGenerator:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        self.model = None
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro')

    def generate_content_ai(self, job_title, company, description, resume_text, user_name):
        """Uses Gemini to write a custom letter."""
        if not self.model: return None
        
        prompt = f"""
        Write a professional cover letter for {user_name} applying to {job_title} at {company}.
        
        Job Description: {description[:1000]}...
        Resume Summary: {resume_text[:1000]}...
        
        Style: Professional, concise, enthusiastic. Max 250 words.
        Structure:
        - Dear Hiring Manager,
        - Para 1: Hook about the company/role.
        - Para 2: Match skills to requirements.
        - Para 3: Call to action.
        - Sincerely, {user_name}
        """
        try:
            resp = self.model.generate_content(prompt)
            return resp.text
        except Exception as e:
            logger.error(f"Cover Letter Gen Failed: {e}")
            return None

    def create_pdf(self, job, resume, user, output_path="generated_cl.pdf"):
        """Generates PDF file."""
        # 1. Generate Text
        content = self.generate_content_ai(job.title, job.company, job.description, resume.raw_text, user.name)
        
        if not content:
            # Fallback Template
            content = f"""
            Dear Hiring Manager,

            I am writing to express my strong interest in the {job.title} position at {job.company}.
            
            With my background and experience, I am confident in my ability to contribute effectively to your team. I have reviewed the job description and believe my skills align well with the requirements.

            Thank you for considering my application. I look forward to the possibility of discussing this exciting opportunity.

            Sincerely,
            {user.name}
            """
        
        # 2. Create PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        
        # Header
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(200, 10, txt=f"Application for {job.title}", ln=1, align='C')
        pdf.ln(10)
        
        # Body
        pdf.set_font("Arial", size=11)
        # FPDF requires latin-1 encoding usually, handle basic unicode replacement
        sanitized = content.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 10, txt=sanitized)
        
        pdf.output(output_path)
        logger.info(f"Generated Cover Letter: {output_path}")
        return output_path

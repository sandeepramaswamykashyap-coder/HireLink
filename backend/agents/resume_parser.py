import fitz  # PyMuPDF
import spacy
import re
from backend.utils.logger import logger
from backend.database import Resume, get_db

# Safe Data Transfer Object (POJO)
class SimpleResume:
    def __init__(self, id, parsed_data):
        self.id = id
        self.parsed_data = parsed_data

class ResumeParser:
    def __init__(self):
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except:
            logger.warning("spaCy model not found, downloading...")
            from spacy.cli import download
            download("en_core_web_sm")
            self.nlp = spacy.load("en_core_web_sm")

    def extract_text(self, file_path):
        """Extract text from PDF"""
        try:
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text()
            return text
        except Exception as e:
            logger.error(f"Error reading PDF {file_path}: {e}")
            return ""

    def extract_email(self, text):
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        matches = re.findall(email_pattern, text)
        return matches[0] if matches else None

    def extract_phone(self, text):
        # Basic Indian phone number regex
        phone_pattern = r'(\+91[\-\s]?)?[6789]\d{9}'
        matches = re.findall(phone_pattern, text)
        if matches:
            full_matches = list(re.finditer(phone_pattern, text))
            if full_matches:
                return full_matches[0].group()
        return None

    def extract_name(self, text):
        # Heuristic: First line or using Spacy PERSON
        doc = self.nlp(text)
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                return ent.text
        return "Unknown"

    def extract_skills(self, text):
        common_skills = ["Python", "Java", "C++", "SQL", "React", "Node.js", "AWS", "Docker", "Kubernetes", "Machine Learning", "Data Science", "Flask", "Django", "HTML", "CSS", "JavaScript"]
        found_skills = []
        lower_text = text.lower()
        for skill in common_skills:
            if skill.lower() in lower_text:
                found_skills.append(skill)
        return found_skills

    def parse_and_save(self, file_path):
        text = self.extract_text(file_path)
        if not text:
            return None
        
        data = {
            "name": self.extract_name(text),
            "email": self.extract_email(text),
            "phone": self.extract_phone(text),
            "skills": self.extract_skills(text)
        }
        
        # Save to DB
        from backend.database import SessionLocal
        db = SessionLocal()
        try:
            resume = Resume(
                name=data['name'],
                email=data['email'],
                phone=data['phone'],
                raw_text=text,
                parsed_data=data,
                file_path=file_path
            )
            db.add(resume)
            db.commit()
            db.refresh(resume) # Get ID
            
            # CRITICAL: Create Safe Return Object (POJO) to avoid Separation logic issues
            safe_resume = SimpleResume(resume.id, data)
            logger.info(f"Parsed and saved resume for {data['name']}")
            
            return safe_resume # Return POJO, NOT the SQLAlchemy object
            
        except Exception as e:
            logger.error(f"Error saving resume: {e}")
            db.rollback()
            return None
        finally:
            db.close()

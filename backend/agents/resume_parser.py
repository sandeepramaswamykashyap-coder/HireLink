import fitz  # PyMuPDF
try:
    import spacy
except ImportError:
    spacy = None
import re
from backend.utils.logger import logger
from backend.database import Resume, get_db
from backend.utils.llm_client import LLMClient
from datetime import datetime
import json

# Safe Data Transfer Object (POJO)
class SimpleResume:
    def __init__(self, id, parsed_data):
        self.id = id
        self.parsed_data = parsed_data

class ResumeParserV2:
    def __init__(self):
        self.llm_client = LLMClient()
        try:
             # self.nlp = spacy.load("en_core_web_sm") 
             # PERFORMANCE OPTIMIZATION: Skip Spacy for now to prevent hangs on cloud
             self.nlp = None
        except:
             logger.warning("spaCy model load failed. Proceeding without NLP.")
             self.nlp = None

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

    # --- REGEX FALLBACKS ---
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
        if not self.nlp:
             # Fallback: Smart Scan of first 10 lines
             lines = [l.strip() for l in text.split('\n') if l.strip()]
             
             # Common headers to ignore
             ignore_terms = ["resume", "cv", "curriculum", "vitae", "profile", "bio", "summary", "contact", "phone", "email", "address"]
             
             for line in lines[:10]:
                 # clean line
                 l_lower = line.lower()
                 
                 # Skip if contains ignore terms
                 if any(term in l_lower for term in ignore_terms):
                     continue
                 
                 # Skip if looks like phone/email
                 if "@" in line or any(c.isdigit() for c in line):
                     continue
                     
                 # If it passes filters and is essentially 2-3 words (Title Case often)
                 words = line.split()
                 if 1 < len(words) <= 4:
                     return line
            
             # If all else fails
             return lines[0] if lines else "Unknown"

        doc = self.nlp(text)
        
        # Blacklist of common false positives
        blacklist = {
            "jira", "python", "sql", "java", "react", "aws", "docker", "kubernetes", "c++", 
            "html", "css", "javascript", "developer", "engineer", "resume", "cv", "curriculum", "vitae",
            "experience", "summary", "skills", "education", "contact", "email", "phone", "address",
            "project", "projects", "work", "history", "profile", "objective", "declaration",
            "date", "place", "signature", "name", "dob", "gender", "nationality", "marital", "status"
        }
        
        candidates = []
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                cleaned_name = ent.text.strip()
                # Validation:
                # 1. Length > 2
                # 2. Not in blacklist
                # 3. No digits
                # 4. At least 2 words? (Maybe singular names allowed but rare)
                
                if len(cleaned_name) > 2 and \
                   cleaned_name.lower() not in blacklist and \
                   not any(char.isdigit() for char in cleaned_name):
                    candidates.append(cleaned_name)
                    
        # Prefer the first candidate that looks reasonable (2+ words)
        for c in candidates:
            if " " in c:
                return c
                
        # Fallback to first single word candidate if no multi-word found
        if candidates:
            return candidates[0]
            
        return "Unknown"

    def extract_skills(self, text):
        common_skills = ["Python", "Java", "C++", "SQL", "React", "Node.js", "AWS", "Docker", "Kubernetes", "Machine Learning", "Data Science", "Flask", "Django", "HTML", "CSS", "JavaScript"]
        found_skills = []
        lower_text = text.lower()
        for skill in common_skills:
            if skill.lower() in lower_text:
                found_skills.append(skill)
        return found_skills

    # --- LLM EXTRACTION ---
    def extract_with_llm(self, text):
        prompt = f"""
        You are an expert Resume Parser. Extract the following details from the resume text below into a valid JSON object.
        
        Fields required:
        - name (string)
        - email (string)
        - phone (string)
        - skills (list of strings)
        - experience (list of objects with 'role', 'company', 'years', 'description')
        - education (list of objects with 'degree', 'school', 'year')
        - summary (string: brief professional summary)

        Resume Text:
        {text[:4000]} 
        """
        # Truncate text to avoid token limits if necessary, though Gemini handles large context well.
        
        return self.llm_client.generate_json(prompt)

    def parse_and_save(self, file_path):
        text = self.extract_text(file_path)
        if not text:
            return None
        
        data = {}
        
        # 1. Try LLM Extraction
        if self.llm_client.client:
            logger.info("Attempting LLM extraction...")
            llm_data = self.extract_with_llm(text)
            if llm_data:
                data = llm_data
                logger.info("LLM extraction successful.")
            else:
                logger.warning("LLM extraction failed or returned empty. Falling back to specific extractors.")
        
        # 2. Fallback / Fill missing with Regex
        if not data.get('email'): data['email'] = self.extract_email(text)
        if not data.get('phone'): data['phone'] = self.extract_phone(text)
        if not data.get('name') or data['name'] == "Unknown": data['name'] = self.extract_name(text)
        if not data.get('skills'): data['skills'] = self.extract_skills(text)
        
        # Ensure regex email matches what is in data if data is empty
        # If LLM failed completely
        if not data:
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
            # DEDUPLICATION CHECK
            existing_resume = None
            if data.get('email'):
                existing_resume = db.query(Resume).filter(Resume.email == data.get('email')).first()
            
            if existing_resume:
                logger.info(f"♻️ Updating existing resume for {data.get('email')}")
                # Update fields
                existing_resume.name = data.get('name')
                existing_resume.phone = data.get('phone')
                existing_resume.raw_text = text
                existing_resume.parsed_data = data
                existing_resume.file_path = file_path
                existing_resume.created_at = datetime.utcnow() # Touch timestamp
                
                db.commit()
                db.refresh(existing_resume)
                resume = existing_resume
            else:
                logger.info(f"✨ Creating new resume for {data.get('email')}")
                resume = Resume(
                    name=data.get('name'),
                    email=data.get('email'),
                    phone=data.get('phone'),
                    raw_text=text,
                    parsed_data=data,
                    file_path=file_path
                )
                db.add(resume)
                db.commit()
                db.refresh(resume) # Get ID
            
            # CRITICAL: Create Safe Return Object (POJO) to avoid Separation logic issues
            safe_resume = SimpleResume(resume.id, data)
            logger.info(f"Parsed and saved/updated resume for {data.get('name')}")
            
            return safe_resume # Return POJO, NOT the SQLAlchemy object
            
        except Exception as e:
            logger.error(f"Error saving resume: {e}")
            db.rollback()
            return None
        finally:
            db.close()

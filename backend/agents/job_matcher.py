from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from backend.database import get_db, Job, Resume, Application
from backend.utils.logger import logger
import pandas as pd
import numpy as np
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import google.generativeai as genai
import os
import json

# Ensure NLTK data is ready
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')

class JobMatcher:
    def __init__(self):
        self.stop_words = set(stopwords.words('english'))
        self.vectorizer = TfidfVectorizer(stop_words='english')
        
        # Gemini Init
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro')
            self.use_llm = True
        else:
            self.use_llm = False
            logger.warning("GEMINI_API_KEY not found. Using Legacy Matcher only.")

    def _preprocess(self, text):
        """Advanced NLP Preprocessing using NLTK"""
        if not text: return ""
        try:
            tokens = word_tokenize(text.lower())
            filtered = [t for t in tokens if t.isalnum() and t not in self.stop_words]
            return " ".join(filtered)
        except: return text

    def match_jobs(self, resume_id, limit=5, days_lookback=30):
        """
        Hybrid Matcher:
        1. Uses TF-IDF (Legacy) to filter top 20 candidates.
        2. Uses Gemini 1.5 (LLM) to score the top candidates deeply.
        """
        # 1. Get Legacy Matches (Broad Filter)
        legacy_matches = self._match_legacy(resume_id, limit=20, days_lookback=days_lookback)
        
        if not self.use_llm or not legacy_matches:
            return legacy_matches[:limit]
            
        # 2. Re-rank with Gemini
        logger.info(f"Refining {len(legacy_matches)} matches with Gemini 1.5...")
        refined_matches = []
        
        db = next(get_db())
        resume = db.query(Resume).get(resume_id)
        resume_text = resume.raw_text[:4000] # Truncate for safety
        
        for item in legacy_matches:
            job = item['job']
            try:
                llm_score, reason = self._score_with_gemini(resume_text, job)
                item['score'] = llm_score
                item['reason'] = reason
                refined_matches.append(item)
            except Exception as e:
                logger.error(f"Gemini scoring failed for Job {job.id}: {e}")
                refined_matches.append(item) # Keep legacy score
        
        # Sort by new LLM score
        refined_matches.sort(key=lambda x: x['score'], reverse=True)
        return refined_matches[:limit]

    def _score_with_gemini(self, resume_text, job):
        """Asks Gemini to score the match 0-100."""
        prompt = f"""
        Role: Expert Technical Recruiter.
        Task: Rate the fit of this candidate for the job.
        
        Job Title: {job.title}
        Job Description: {job.description[:2000]}
        
        Candidate Resume: {resume_text}
        
        Output JSON only:
        {{
            "score": <0-100 integer>,
            "reason": "<1 short sentence explaining why>"
        }}
        """
        response = self.model.generate_content(prompt)
        try:
            data = json.loads(response.text.replace("```json", "").replace("```", ""))
            return data.get("score", 50), data.get("reason", "AI analysis")
        except:
            return 50, "Analysis failed"

    def _match_legacy(self, resume_id, limit=50, days_lookback=30):
        db = next(get_db())
        
        # Get Resume
        resume = db.query(Resume).filter_by(id=resume_id).first()
        if not resume: return []
            
        # 1. Get IDs of jobs already applied to
        applied_job_ids = [app.job_id for app in db.query(Application.job_id).all()]
        
        # 2. Query Jobs
        from datetime import datetime, timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days_lookback)
        jobs_query = db.query(Job).filter(Job.scraped_date >= cutoff_date)
        if applied_job_ids:
            jobs_query = jobs_query.filter(~Job.id.in_(applied_job_ids))
        jobs = jobs_query.all()
        
        if not jobs: return []
            
        # Prepare Data
        resume_text = self._preprocess(resume.raw_text)
        job_descriptions = [self._preprocess(f"{j.title} {j.skills} {j.description}") for j in jobs]
        
        # TF-IDF
        all_docs = [resume_text] + job_descriptions
        tfidf_matrix = self.vectorizer.fit_transform(all_docs)
        cosine_sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
        base_scores = np.round(cosine_sim * 100, 2)
        
        # Keyword Bonus
        resume_skills_set = set()
        if resume.parsed_data and 'skills' in resume.parsed_data:
             resume_skills_set = {str(s).lower() for s in resume.parsed_data['skills']}
        
        matched_jobs = []
        for i, score in enumerate(base_scores):
            job = jobs[i]
            bonus = 0
            if resume_skills_set:
                job_blob = (str(job.skills) + " " + str(job.description)).lower()
                for skill in resume_skills_set:
                    if skill in job_blob: bonus += 15
                bonus = min(60, bonus)
            
            final_score = min(98.0, score + bonus)
            if resume.name and job.title and any(part.lower() in job.title.lower() for part in resume.raw_text.split()[:5]):
                 final_score = min(99.0, final_score + 25)

            matched_jobs.append({
                "job": job,
                "score": float(final_score),
                "debug_base": float(score),
                "debug_bonus": float(bonus)
            })
            
        matched_jobs.sort(key=lambda x: x['score'], reverse=True)
        return matched_jobs[:limit]

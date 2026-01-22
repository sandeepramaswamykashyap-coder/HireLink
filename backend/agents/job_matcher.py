from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from backend.database import get_db, Job, Resume
from backend.utils.logger import logger
import pandas as pd
import numpy as np
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

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

    def _preprocess(self, text):
        """Advanced NLP Preprocessing using NLTK"""
        if not text: return ""
        tokens = word_tokenize(text.lower())
        filtered = [t for t in tokens if t.isalnum() and t not in self.stop_words]
        return " ".join(filtered)

    def match_jobs(self, resume_id, limit=50, days_lookback=30):
        db = next(get_db())
        from datetime import datetime, timedelta
        from backend.database import Application # Ensure imported
        
        # Get Resume
        resume = db.query(Resume).filter_by(id=resume_id).first()
        if not resume:
            logger.error(f"Resume {resume_id} not found")
            return []
            
        # 1. Get IDs of jobs already applied to
        applied_job_ids = [app.job_id for app in db.query(Application.job_id).all()]
        
        # 2. Query Jobs: Not Applied AND Recent
        cutoff_date = datetime.utcnow() - timedelta(days=days_lookback)
        jobs_query = db.query(Job).filter(
            Job.scraped_date >= cutoff_date
        )
        
        if applied_job_ids:
            jobs_query = jobs_query.filter(~Job.id.in_(applied_job_ids))
            
        jobs = jobs_query.all()
        
        if not jobs:
            return []
            
        # Prepare Data (Preprocessed with NLTK)
        resume_text = self._preprocess(resume.raw_text)
        job_descriptions = [self._preprocess(f"{j.title} {j.skills} {j.description}") for j in jobs]
        
        # TF-IDF
        all_docs = [resume_text] + job_descriptions
        tfidf_matrix = self.vectorizer.fit_transform(all_docs)
        
        # Calculate Cosine Similarity
        cosine_sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
        
        # NumPy Vectorized Rounding
        base_scores = np.round(cosine_sim * 100, 2)
        
        # --- CALIBRATION: KEYWORD BONUS ---
        # Pure TF-IDF matches poorly on short texts. We add a bonus for hard skill overlap.
        resume_skills_set = set()
        if resume.parsed_data and 'skills' in resume.parsed_data:
             # Normalize skills
             resume_skills_set = {str(s).lower() for s in resume.parsed_data['skills']}
        
        # Rank Results
        matched_jobs = []
        for i, score in enumerate(base_scores):
            job = jobs[i]
            
            # Calculate Bonus
            bonus = 0
            debug_matches = []
            if resume_skills_set:
                job_blob = (str(job.skills) + " " + str(job.description)).lower()
                for skill in resume_skills_set:
                    if skill in job_blob:
                        bonus += 15
                        debug_matches.append(skill)
                
                # Cap bonus
                bonus = min(60, bonus)
                if bonus > 0:
                    logger.info(f"MATCH DEBUG: Job {job.id} matched skills: {debug_matches} -> Bonus: {bonus}")
            
            final_score = min(98.0, score + bonus)
            
            # Boost matches with title overlap
            if resume.name and job.title and any(part.lower() in job.title.lower() for part in resume.raw_text.split()[:5]):
                 final_score = min(99.0, final_score + 25)

            matched_jobs.append({
                "job": job,
                "score": float(final_score),
                "debug_base": float(score),
                "debug_bonus": float(bonus)
            })
            
        # Sort by score desc
        matched_jobs.sort(key=lambda x: x['score'], reverse=True)
        return matched_jobs[:limit]

    def match_question(self, target_question, knowledge_base):
        """
        Finds the best matching answer from the knowledge base for a given target question.
        Args:
            target_question (str): The question asked by the portal.
            knowledge_base (dict): { "category": { "question": "answer" } } OR flat { "question": "answer" }
        Returns:
            answer (str) or None
        """
        if not target_question or not knowledge_base: return None
        
        # Flatten KB if needed
        flat_kb = {}
        for k, v in knowledge_base.items():
            if isinstance(v, dict):
                for q, a in v.items():
                    flat_kb[q] = a
            else:
                flat_kb[k] = v
                
        if not flat_kb: return None
        
        known_questions = list(flat_kb.keys())
        
        # Preprocess
        target_proc = self._preprocess(target_question)
        known_proc = [self._preprocess(q) for q in known_questions]
        
        # Quick exact/substring check first (Optimization)
        for i, q_proc in enumerate(known_proc):
            if target_proc == q_proc or target_proc in q_proc or q_proc in target_proc:
                return flat_kb[known_questions[i]]
        
        # TF-IDF Cosine Similarity
        try:
            all_docs = [target_proc] + known_proc
            # Fit specific for this batch to ensure vocabulary covers these specific words
            # Note: We reuse the vectorizer config but fit_transform on new data
            local_vectorizer = TfidfVectorizer(stop_words='english')
            tfidf_matrix = local_vectorizer.fit_transform(all_docs)
            
            cosine_sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
            
            best_idx = np.argmax(cosine_sim)
            best_score = cosine_sim[best_idx]
            
            logger.info(f"Smart Answer Match: '{target_question}' matched '{known_questions[best_idx]}' (Score: {best_score:.2f})")
            
            # Threshold (e.g., 0.4 implies distinct similarity)
            if best_score > 0.35:
                return flat_kb[known_questions[best_idx]]
            
        except Exception as e:
            logger.error(f"Semantic Match Failed: {e}")
            
        return None

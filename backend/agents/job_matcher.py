from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from backend.database import get_db, Job, Resume
from backend.utils.logger import logger
import pandas as pd

class JobMatcher:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english')

    def match_jobs(self, resume_id, limit=50):
        db = next(get_db())
        
        # Get Resume
        resume = db.query(Resume).filter_by(id=resume_id).first()
        if not resume:
            logger.error(f"Resume {resume_id} not found")
            return []
            
        # Get Jobs
        jobs = db.query(Job).all()
        if not jobs:
            return []
            
        # Prepare Data
        resume_text = resume.raw_text
        job_descriptions = [f"{j.title} {j.skills} {j.description}" for j in jobs]
        
        # TF-IDF
        all_docs = [resume_text] + job_descriptions
        tfidf_matrix = self.vectorizer.fit_transform(all_docs)
        
        # Calculate Cosine Similarity
        # Index 0 is resume, 1..N are jobs
        cosine_sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
        
        # Rank Results
        matched_jobs = []
        for i, score in enumerate(cosine_sim):
            job = jobs[i]
            matched_jobs.append({
                "job": job,
                "score": round(score * 100, 2)
            })
            
        # Sort by score desc
        matched_jobs.sort(key=lambda x: x['score'], reverse=True)
        return matched_jobs[:limit]

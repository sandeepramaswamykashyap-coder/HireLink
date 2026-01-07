from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from backend.database import get_db, Job, Resume
from backend.utils.logger import logger
import pandas as pd

class JobMatcher:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english')

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

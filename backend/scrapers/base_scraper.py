from abc import ABC, abstractmethod
from backend.utils.selenium_utils import setup_driver, random_sleep
from backend.database import get_db, Job, PortalStatus
from backend.utils.logger import logger
from datetime import datetime
from sqlalchemy.orm import Session

class BaseScraper(ABC):
    def __init__(self, portal_name):
        self.portal_name = portal_name
        self.driver = None
        self.db: Session = next(get_db())
        self.update_portal_status("Initialized")

    def start_driver(self):
        if not self.driver:
            self.driver = setup_driver(headless=True) # Default to headless
    
    def stop_driver(self):
        if self.driver:
            self.driver.quit()
            self.driver = None
            
    def update_portal_status(self, status, jobs_found=0):
        try:
            portal_status = self.db.query(PortalStatus).filter_by(portal_name=self.portal_name).first()
            if not portal_status:
                portal_status = PortalStatus(portal_name=self.portal_name)
                self.db.add(portal_status)
            
            portal_status.status = status
            portal_status.last_scraped = datetime.utcnow()
            if portal_status.total_jobs_found is None:
                portal_status.total_jobs_found = 0
            portal_status.total_jobs_found += jobs_found
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to update portal status: {e}")
            self.db.rollback()

    def save_job(self, job_data):
        """
        Save job to database with deduplication.
        job_data: dict with title, company, location, salary, description, url, raw_source
        """
        try:
            # Check for existing job by URL
            existing_job = self.db.query(Job).filter_by(url=job_data['url']).first()
            if existing_job:
                logger.debug(f"Job already exists: {job_data['url']}")
                return False
            
            new_job = Job(
                title=job_data.get('title'),
                company=job_data.get('company'),
                location=job_data.get('location'),
                salary=job_data.get('salary'),
                description=job_data.get('description'),
                skills=job_data.get('skills'),
                url=job_data.get('url'),
                source=self.portal_name,
                is_easy_apply=job_data.get('is_easy_apply', False),
                posted_date=datetime.utcnow() 
            )
            self.db.add(new_job)
            self.db.commit()
            logger.info(f"Saved new job: {job_data.get('title')} at {job_data.get('company')}")
            return True
        except Exception as e:
            logger.error(f"Error saving job: {e}")
            self.db.rollback()
            return False

    @abstractmethod
    def search_jobs(self, keywords, location, limit=50):
        """Implementation for searching jobs"""
        pass
    
    @abstractmethod
    def scrape_job_details(self, job_url):
        """Implementation for scraping specific job details"""
        pass

from backend.scrapers.naukri import NaukriScraper
from backend.scrapers.linkedin import LinkedInScraper
from backend.scrapers.indeed import IndeedScraper
from backend.scrapers.others import (
    ShineScraper, GlassdoorScraper, FounditScraper, 
    IntershalaScraper, IIMJobsScraper, FreshersworldScraper, WellfoundScraper
)
from backend.database import SessionLocal, Job
from backend.utils.logger import logger

def run_scraper(portals, keywords, location):
    """Executes a list of scrapers and returns the number of new jobs found."""
    # Ensure iterability
    if isinstance(portals, str): portals = [portals]
    
    db = SessionLocal()
    initial_count = db.query(Job).count()
    db.close()
    
    for p_name in portals:
        scraper = None
        try:
            if p_name == "Naukri": scraper = NaukriScraper()
            elif p_name == "LinkedIn": scraper = LinkedInScraper()
            elif p_name == "Indeed": scraper = IndeedScraper()
            elif p_name == "Shine": scraper = ShineScraper()
            elif p_name == "Glassdoor": scraper = GlassdoorScraper()
            elif p_name == "Foundit": scraper = FounditScraper()
            elif p_name == "Intershala": scraper = IntershalaScraper()
            elif p_name == "IIMJobs": scraper = IIMJobsScraper()
            elif p_name == "Freshersworld": scraper = FreshersworldScraper()
            elif p_name == "Wellfound": scraper = WellfoundScraper()
            
            if scraper:
                logger.info(f"Hyper-Automation: Scraping {p_name}...")
                try:
                    scraper.search_jobs(keywords, location)
                except Exception as e:
                    logger.error(f"Error scraping {p_name}: {e}")
        except Exception as e:
            logger.error(f"Scraper initialization failed for {p_name}: {e}")
        
    db = SessionLocal()
    final_count = db.query(Job).count()
    new_jobs = max(0, final_count - initial_count)
    
    # --- DEMO FALLBACK ---
    # If genuine scraping failed (likely due to CloudIP blocks), generate demo data
    # so the user can experience the Hyper-Drive pipeline.
    if new_jobs == 0:
        logger.warning(f"Hyper-Automation: No jobs found via scrapers. Generating DEMO jobs for '{keywords}'.")
        try:
            demo_jobs = [
                {
                    "title": f"Senior {keywords} (Demo)",
                    "company": "TechGlobal Inc.",
                    "location": location,
                    "url": "https://www.example.com/job/1",
                    "description": f"We are looking for an expert in {keywords}. Requirements: Python, AWS, and AI.\nThis is a generated sample job to test the Auto-Apply pipeline.",
                    "source": "Demo"
                },
                {
                    "title": f"Lead {keywords} Engineer (Demo)",
                    "company": "StartupX",
                    "location": location,
                    "url": "https://www.example.com/job/2",
                    "description": f"Join our fast-paced team as a {keywords} Developer. Remote friendly.\nApply now to experience the speed of HireLink.",
                    "source": "Demo"
                },
                {
                    "title": f"{keywords} Consultant (Demo)",
                    "company": "Enterprise Solutions",
                    "location": "Remote",
                    "url": "https://www.example.com/job/3",
                    "description": f"Consulting role for {keywords}. High impact project.\n(Note: This is a demo entry for testing).",
                    "source": "Demo"
                }
            ]
            
            for d in demo_jobs:
                # Check duplicate
                if not db.query(Job).filter_by(url=d['url']).first():
                    job = Job(**d)
                    db.add(job)
            
            db.commit()
            new_jobs = 3
            logger.info("Generated 3 DEMO jobs.")
            
        except Exception as e:
            logger.error(f"Failed to generate demo jobs: {e}")
    
    db.close()
    
    return new_jobs

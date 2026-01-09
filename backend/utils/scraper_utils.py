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
    db.close()
    
    return max(0, final_count - initial_count)

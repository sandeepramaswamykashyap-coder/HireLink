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
    """
    Executes a list of scrapers and returns the number of new jobs found.
    Supports keywords and location as lists or comma-separated strings.
    """
    # Ensure iterability for portals
    if isinstance(portals, str): portals = [portals]
    
    # Parse keywords and locations into normalized lists
    if isinstance(keywords, str):
        kw_list = [k.strip() for k in keywords.split(",") if k.strip()]
    else:
        kw_list = keywords if isinstance(keywords, list) else [keywords]
        
    if isinstance(location, str):
        loc_list = [l.strip() for l in location.split(",") if l.strip()]
    else:
        loc_list = location if isinstance(location, list) else [location]

    # Fallback to single item if list is empty
    if not kw_list: kw_list = ["Software Engineer"]
    if not loc_list: loc_list = ["Remote"]

    db = SessionLocal()
    initial_count = db.query(Job).count()
    db.close()
    
    # Combinatorial Loop: Role x Location x Portal
    for kw in kw_list:
        for loc in loc_list:
            for p_name in portals:
                scraper = None
                try:
                    if p_name == "Naukri": scraper = NaukriScraper()
                    elif p_name == "LinkedIn": scraper = LinkedInScraper()
                    elif p_name == "Indeed": scraper = IndeedScraper()
                    elif p_name == "Shine": scraper = ShineScraper()
                    elif p_name == "Glassdoor": 
                        from backend.scrapers.glassdoor import GlassdoorScraper
                        scraper = GlassdoorScraper()
                    elif p_name == "Foundit": scraper = FounditScraper()
                    elif p_name == "Intershala": scraper = IntershalaScraper()
                    elif p_name == "IIMJobs": scraper = IIMJobsScraper()
                    elif p_name == "Freshersworld": scraper = FreshersworldScraper()
                    elif p_name == "Wellfound": scraper = WellfoundScraper()
                    
                    if scraper:
                        logger.info(f"Hyper-Automation: Scraping {p_name} for '{kw}' in '{loc}'...")
                        try:
                            scraper.search_jobs(kw, loc)
                        except Exception as e:
                            logger.error(f"Error scraping {p_name}: {e}")
                except Exception as e:
                    logger.error(f"Scraper initialization failed for {p_name}: {e}")
    
    db = SessionLocal()
    final_count = db.query(Job).count()
    new_jobs = max(0, final_count - initial_count)
    
    # --- DEMO FALLBACK ---
    if new_jobs == 0:
        logger.warning(f"Hyper-Automation: No jobs found. Generating DEMO jobs for '{kw_list[0]}' in '{loc_list[0]}'.")
        try:
            # Just generate for the first combination to avoid flooding DB with demos
            demo_kw = kw_list[0]
            demo_loc = loc_list[0]
            demo_jobs = [
                {
                    "title": f"Senior {demo_kw} (Demo)",
                    "company": "TechGlobal Inc.",
                    "location": demo_loc,
                    "url": "https://www.example.com/job/1",
                    "description": f"Expert in {demo_kw} required. Keywords: {', '.join(kw_list)}.",
                    "source": "Demo"
                },
                {
                    "title": f"Lead {demo_kw} Engineer (Demo)",
                    "company": "StartupX",
                    "location": demo_loc,
                    "url": "https://www.example.com/job/2",
                    "description": f"Join our team as a {demo_kw}. Remote friendly.\nLocations: {', '.join(loc_list)}.",
                    "source": "Demo"
                }
            ]
            
            added = 0
            for d in demo_jobs:
                if not db.query(Job).filter_by(url=d['url']).first():
                    job = Job(**d)
                    db.add(job)
                    added += 1
            
            db.commit()
            new_jobs = added
            logger.info(f"Generated {added} DEMO jobs.")
            
        except Exception as e:
            logger.error(f"Failed to generate demo jobs: {e}")
    
    db.close()
    return new_jobs

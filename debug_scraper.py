from backend.scrapers.naukri import NaukriScraper
from backend.scrapers.linkedin import LinkedInScraper
from backend.scrapers.indeed import IndeedScraper
from backend.scrapers.others import (
    ShineScraper, GlassdoorScraper, FounditScraper, 
    IntershalaScraper, IIMJobsScraper, FreshersworldScraper, WellfoundScraper
)
import logging

logging.basicConfig(level=logging.INFO)

def test_all():
    scrapers = [
        NaukriScraper
    ]
    
    for ScraperClass in scrapers:
        s_name = ScraperClass().__class__.__name__
        print(f"\n{'='*20}\nTesting {s_name}...\n{'='*20}")
        try:
            s = ScraperClass()
            s.search_jobs("python developer", "bangalore")
        except Exception as e:
            print(f"FAILED {s_name}: {e}")

if __name__ == "__main__":
    test_all()

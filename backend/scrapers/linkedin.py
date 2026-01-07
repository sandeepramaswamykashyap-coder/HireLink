from backend.scrapers.base_scraper import BaseScraper
from backend.utils.selenium_utils import random_sleep
from backend.utils.logger import logger
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class LinkedInScraper(BaseScraper):
    def __init__(self):
        super().__init__("LinkedIn")
        self.base_url = "https://www.linkedin.com/jobs/search"

    def search_jobs(self, keywords, location, limit=20):
        self.start_driver()
        jobs_found_count = 0
        try:
            self.update_portal_status("Scraping")
            
            # Use Guest Search URL (No login required for basic scrape)
            # https://www.linkedin.com/jobs/search?keywords=Python&location=India
            search_url = f"{self.base_url}?keywords={keywords}&location={location}"
            
            logger.info(f"Navigating to {search_url}")
            self.driver.get(search_url)
            random_sleep(3, 5)
            
            # Scroll a bit
            body = self.driver.find_element(By.TAG_NAME, "body")
            for _ in range(5):
                body.send_keys(Keys.PAGE_DOWN)
                random_sleep(0.5, 1)
            
            job_cards = self.driver.find_elements(By.CLASS_NAME, "base-card")
            logger.info(f"Found {len(job_cards)} job cards")
            
            for card in job_cards:
                if jobs_found_count >= limit:
                    break
                
                try:
                    # Extract Data
                    title_elem = card.find_element(By.CLASS_NAME, "base-search-card__title")
                    company_elem = card.find_element(By.CLASS_NAME, "base-search-card__subtitle")
                    loc_elem = card.find_element(By.CLASS_NAME, "job-search-card__location")
                    link_elem = card.find_element(By.CLASS_NAME, "base-card__full-link")
                    
                    job_url = link_elem.get_attribute("href")
                    
                    job_data = {
                        "title": title_elem.text.strip(),
                        "company": company_elem.text.strip(),
                        "location": loc_elem.text.strip(),
                        "url": job_url,
                        "description": "See Link",
                        "salary": "Not Disclosed",
                        "source": "LinkedIn",
                        "skills": ""
                    }
                    
                    if self.save_job(job_data):
                        jobs_found_count += 1
                        
                except Exception as e:
                    # Creating a new card or element issue
                    continue
            
            self.update_portal_status("Idle", jobs_found=jobs_found_count)
            logger.info(f"LinkedIn scrape complete. Found {jobs_found_count} new jobs.")
            
        except Exception as e:
            logger.error(f"LinkedIn scrape failed: {e}")
            self.update_portal_status("Error")
        finally:
            self.stop_driver()

    def scrape_job_details(self, job_url):
        pass

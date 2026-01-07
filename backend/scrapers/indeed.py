from backend.scrapers.base_scraper import BaseScraper
from backend.utils.selenium_utils import random_sleep
from backend.utils.logger import logger
from selenium.webdriver.common.by import By
import urllib.parse

class IndeedScraper(BaseScraper):
    def __init__(self):
        super().__init__("Indeed")
        self.base_url = "https://in.indeed.com"

    def search_jobs(self, keywords, location, limit=20):
        self.start_driver()
        jobs_found_count = 0
        try:
            self.update_portal_status("Scraping")
            
            # https://in.indeed.com/jobs?q=python&l=bangalore
            q = urllib.parse.quote(keywords)
            l = urllib.parse.quote(location)
            search_url = f"{self.base_url}/jobs?q={q}&l={l}"
            
            logger.info(f"Navigating to {search_url}")
            self.driver.get(search_url)
            random_sleep(3, 6)
            
            job_cards = self.driver.find_elements(By.CLASS_NAME, "job_seen_beacon")
            logger.info(f"Found {len(job_cards)} job cards on Indeed")
            
            for card in job_cards:
                if jobs_found_count >= limit:
                    break
                try:
                    title_elem = card.find_element(By.CLASS_NAME, "jobTitle")
                    company_elem = card.find_element(By.CSS_SELECTOR, "[data-testid='company-name']")
                    loc_elem = card.find_element(By.CSS_SELECTOR, "[data-testid='text-location']")
                    
                    # Indeed tricky URL extraction
                    link_elem = title_elem.find_element(By.TAG_NAME, "a")
                    job_url = link_elem.get_attribute("href")
                    
                    job_data = {
                        "title": title_elem.text,
                        "company": company_elem.text,
                        "location": loc_elem.text,
                        "url": job_url,
                        "source": "Indeed"
                    }
                    
                    if self.save_job(job_data):
                        jobs_found_count += 1
                except:
                    continue
            
            self.update_portal_status("Idle", jobs_found=jobs_found_count)
            
        except Exception as e:
            logger.error(f"Indeed scrape failed: {e}")
            self.update_portal_status("Error")
        finally:
            self.stop_driver()
            
    def scrape_job_details(self, job_url):
        pass

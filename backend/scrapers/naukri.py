from backend.scrapers.base_scraper import BaseScraper
from backend.utils.selenium_utils import random_sleep
from backend.utils.logger import logger
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import urllib.parse

class NaukriScraper(BaseScraper):
    def __init__(self):
        super().__init__("Naukri.com")
        self.base_url = "https://www.naukri.com"

    def search_jobs(self, keywords, location, limit=20):
        self.start_driver()
        jobs_found_count = 0
        try:
            self.update_portal_status("Scraping")
            
            # Construct Search URL
            # Format: https://www.naukri.com/python-developer-jobs-in-bangalore
            # This is a bit tricky with Naukri's URL structure, better to use the search bar or query params if possible.
            # Naukri uses a specific URL pattern: https://www.naukri.com/<keywords>-jobs-in-<location>
            
            kw = keywords.replace(" ", "-")
            loc = location.replace(" ", "-")
            search_url = f"{self.base_url}/{kw}-jobs-in-{loc}"
            
            logger.info(f"Navigating to {search_url}")
            self.driver.get(search_url)
            random_sleep(3, 6)
            
            # Wait for job list
            wait = WebDriverWait(self.driver, 10)
            job_tuples_parent = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "list")))
            
            # Scroll to load more if needed (Naukri lazy loads)
            # For simplicity, we just take the first page (~20 jobs)
            
            articles = self.driver.find_elements(By.TAG_NAME, "article")
            logger.info(f"Found {len(articles)} job cards on page 1")
            
            for article in articles:
                if jobs_found_count >= limit:
                    break
                
                try:
                    # Extract basic info from card
                    title_elem = article.find_element(By.CLASS_NAME, "title")
                    company_elem = article.find_element(By.CLASS_NAME, "comp-name")
                    loc_elem = article.find_element(By.CLASS_NAME, "locWdth")
                    url_elem = title_elem # Title is an anchor usually or parent
                    
                    job_url = title_elem.get_attribute("href")
                    title = title_elem.text
                    company = company_elem.text
                    location_text = loc_elem.text
                    
                    # Try to get data
                    job_data = {
                        "title": title,
                        "company": company,
                        "location": location_text,
                        "url": job_url,
                        "description": "See Link", # Full scraping requires visiting each link, can be slow
                        "salary": "Not Disclosed",
                        "skills": "" 
                    }
                    
                    # Optional: Get extra details like salary/exp if visible on card
                    try:
                        salary_elem = article.find_element(By.CLASS_NAME, "sal-wrap")
                        job_data["salary"] = salary_elem.text
                    except:
                        pass
                        
                    if self.save_job(job_data):
                        jobs_found_count += 1
                        
                except Exception as e:
                    logger.warning(f"Error parsing job card: {e}")
                    continue
            
            self.update_portal_status("Idle", jobs_found=jobs_found_count)
            logger.info(f"Naukri scrape complete. Found {jobs_found_count} new jobs.")
            
        except Exception as e:
            logger.error(f"Naukri scrape failed: {e}")
            self.update_portal_status("Error")
        finally:
            self.stop_driver()

    def scrape_job_details(self, job_url):
        # Implementation to visit specific job page and get full description/skills
        pass

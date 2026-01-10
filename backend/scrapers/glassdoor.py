from backend.scrapers.base_scraper import BaseScraper
from backend.utils.selenium_utils import random_sleep
from backend.utils.logger import logger
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

class GlassdoorScraper(BaseScraper):
    def __init__(self):
        super().__init__("Glassdoor")
        # Public search URL structure
        self.base_url = "https://www.glassdoor.co.in/Job/india-{keywords}-jobs-SRCH_IL.0,5_IN115_KO6,{len_keywords}.htm"

    def search_jobs(self, keywords, location, limit=20):
        self.start_driver()
        jobs_found_count = 0
        try:
            self.update_portal_status("Scraping")
            
            # Construct URL (Glassdoor is strict about URL formats)
            # Simplified approach: Use main search and type input
            self.driver.get("https://www.glassdoor.co.in/Job/index.htm")
            random_sleep(3, 5)
            
            try:
                # Type Keywords
                k_input = self.driver.find_element(By.ID, "searchBar-jobTitle")
                k_input.clear()
                k_input.send_keys(keywords)
                random_sleep(1)
                
                # Type Location
                l_input = self.driver.find_element(By.ID, "searchBar-location")
                l_input.clear()
                l_input.send_keys(location)
                random_sleep(1)
                # Select first autocomplete if appears
                l_input.send_keys(Keys.ARROW_DOWN)
                l_input.send_keys(Keys.ENTER)
            except:
                logger.warning("Could not use search bar, trying direct URL injection...")
                safe_kw = keywords.replace(" ", "-")
                self.driver.get(f"https://www.glassdoor.co.in/Job/{safe_kw}-jobs-SRCH_KO0,{len(safe_kw)}.htm")
            
            random_sleep(4, 6)
            
            # Handle "Sign In" Modal (Glassdoor is notorious for this)
            try:
                close_btn = self.driver.find_element(By.CSS_SELECTOR, "button.CloseButton")
                if close_btn: close_btn.click()
            except: pass

            # Scrape Cards
            # Glassdoor selectors change often. Common: li.react-job-listing or li[data-id]
            job_cards = self.driver.find_elements(By.CSS_SELECTOR, "li[data-id]")
            logger.info(f"Found {len(job_cards)} job cards.")
            
            for card in job_cards:
                if jobs_found_count >= limit: break
                
                try:
                    # Extract Data
                    try: 
                        # Title is usually in a link with class 'jobLink'
                        title_elem = card.find_element(By.CSS_SELECTOR, "a.jobLink")
                        title = title_elem.text.strip()
                        url = title_elem.get_attribute("href")
                    except: continue

                    try:
                        # Company is usually separate div
                        company = card.find_element(By.CLASS_NAME, "job-search-key-l2wjgv").text.strip()
                    except: company = "Unknown"
                    
                    try:
                        loc = card.find_element(By.CLASS_NAME, "job-search-key-iii9i8").text.strip()
                    except: loc = location
                    
                    if "Rating" in company: # Cleanup "Company 4.5 ★"
                        company = company.split("\n")[0]

                    job_data = {
                        "title": title,
                        "company": company,
                        "location": loc,
                        "url": url,
                        "description": "See Link", # Glassdoor hides full desc behind click
                        "source": "Glassdoor"
                    }
                    
                    if self.save_job(job_data):
                        jobs_found_count += 1
                        
                except Exception as e:
                    continue
            
            self.update_portal_status("Idle", jobs_found=jobs_found_count)
            logger.info(f"Glassdoor scrape complete. Found {jobs_found_count} new jobs.")

        except Exception as e:
            logger.error(f"Glassdoor scrape failed: {e}")
            self.update_portal_status("Error")
        finally:
            self.stop_driver()

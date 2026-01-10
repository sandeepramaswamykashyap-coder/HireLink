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
            search_url = f"{self.base_url}?keywords={keywords}&location={location}"
            
            logger.info(f"Navigating to {search_url}")
            self.driver.get(search_url)
            random_sleep(3, 5)

            # DISMISS MODALS (Critical for Headless)
            try:
                # Common "Join to view" modal
                close_btns = self.driver.find_elements(By.CSS_SELECTOR, "button[data-tracking-control-name='public_jobs_contextual-sign-in-modal_modal_dismiss']")
                if close_btns: 
                    close_btns[0].click()
                    random_sleep(1)
                
                # "Sign in" CTA bottom banner
                cta_close = self.driver.find_elements(By.CSS_SELECTOR, "button.cta-modal__dismiss-btn")
                if cta_close: cta_close[0].click()

                # Generic "X" buttons
                x_btns = self.driver.find_elements(By.CSS_SELECTOR, "button[aria-label='Dismiss']")
                if x_btns: x_btns[0].click()
            except: pass
            
            # Scroll with JS
            for _ in range(5):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                random_sleep(1, 1.5)
            
            # Robust Selectors
            # Try multiple classes as LinkedIn A/B tests classes frequently
            card_selectors = ["base-card", "job-search-card", "result-card"]
            job_cards = []
            for sel in card_selectors:
                found = self.driver.find_elements(By.CLASS_NAME, sel)
                if found:
                    job_cards = found
                    break
            
            logger.info(f"Found {len(job_cards)} job cards (Selector used: {sel if job_cards else 'None'})")
            
            # Debug if 0
            if len(job_cards) == 0:
                logger.warning(f"Page Title: {self.driver.title}")
                logger.info("Possible anti-bot block or no results.")
            
            for card in job_cards:
                if jobs_found_count >= limit:
                    break
                
                try:
                    # Extract Data with Fallbacks
                    try: title_text = card.find_element(By.CSS_SELECTOR, "h3").text.strip()
                    except: title_text = card.find_element(By.CLASS_NAME, "base-search-card__title").text.strip()
                    
                    try: company_text = card.find_element(By.CSS_SELECTOR, "h4").text.strip()
                    except: company_text = card.find_element(By.CLASS_NAME, "base-search-card__subtitle").text.strip()
                    
                    try: loc_text = card.find_element(By.CLASS_NAME, "job-search-card__location").text.strip()
                    except: loc_text = "Unknown"
                    
                    try: job_url = card.find_element(By.TAG_NAME, "a").get_attribute("href")
                    except: continue # Essential
                    
                    # Validation: Skip obfuscated, empty, or too short data
                    if "*****" in title_text or "*****" in company_text:
                        continue
                    if len(title_text) < 2 or len(company_text) < 2:
                         continue
                        
                    job_data = {
                        "title": title_text,
                        "company": company_text,
                        "location": loc_text,
                        "url": job_url,
                        "description": "See Link",
                        "salary": "Not Disclosed",
                        "source": "LinkedIn",
                        "skills": ""
                    }
                    
                    if self.save_job(job_data):
                        jobs_found_count += 1
                        
                except Exception as e:
                    continue
            
            self.update_portal_status("Idle", jobs_found=jobs_found_count)
            logger.info(f"LinkedIn scrape complete. Found {jobs_found_count} new jobs.")
            
        except Exception as e:
            logger.error(f"LinkedIn scrape failed: {e}")
            self.update_portal_status("Error")
        finally:
            self.stop_driver()

    def scrape_job_details(self, job_url):
        """
        Visits the job URL to scrape full description and metadata.
        """
        self.start_driver()
        try:
            logger.info(f"Scraping detailed description for: {job_url}")
            self.driver.get(job_url)
            random_sleep(2, 4)
            
            # 1. Expand Description (if explicit 'See more' button exists)
            try:
                # Common "See more" buttons on LinkedIn
                buttons = self.driver.find_elements(By.CLASS_NAME, "jobs-description__footer-button")
                for btn in buttons:
                     if "see more" in btn.text.lower() and btn.is_displayed():
                         self.driver.execute_script("arguments[0].click();", btn)
                         random_sleep(1)
            except: pass

            # 2. Extract Description
            # Try multiple selectors for robustness (Public User vs Logged In User)
            description = ""
            selectors = [
                 "div.description__text",          # Public Job Page
                 "div.jobs-description__content",  # Logged In View
                 "div.show-more-less-html__markup" # General Wrapper
            ]
            
            for sel in selectors:
                try:
                    elem = self.driver.find_element(By.CSS_SELECTOR, sel)
                    if elem.is_displayed():
                        description = elem.text.strip()
                        break
                except: continue
            
            if not description:
                logger.warning(f"Could not find description text for {job_url}")
                return None
                
            # 3. Extract Skills (if available in "Skills" section)
            skills = []
            try:
                # Look for "Skills" section in the description or separate component
                # This is hard on LinkedIn as it's often dynamic, but we can try scraping textual keywords
                # Or looking for the "Skills" card
                pass 
            except: pass
            
            return {
                "description": description,
                "skills": ", ".join(skills) if skills else ""
            }

        except Exception as e:
            logger.error(f"Failed to scrape details for {job_url}: {e}")
            return None

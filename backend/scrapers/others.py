from backend.scrapers.base_scraper import BaseScraper
from backend.utils.logger import logger
from backend.utils.selenium_utils import random_sleep

class ShineScraper(BaseScraper):
    def __init__(self):
        super().__init__("Shine")
        self.base_url = "https://www.shine.com"
        
    def search_jobs(self, keywords, location, limit=20):
        self.start_driver()
        jobs_found_count = 0
        try:
            self.update_portal_status("Scraping")
            
            # URL Structure: https://www.shine.com/job-search/python-developer-jobs-in-bangalore?q=python-developer&loc=Bangalore
            kw = keywords.replace(" ", "-")
            url = f"{self.base_url}/job-search/{kw}-jobs-in-{location}?q={kw}&loc={location}"
            
            logger.info(f"Navigating to {url}")
            self.driver.get(url)
            random_sleep(3, 5)
            
            # Detailed Wait
            try:
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='jobCard'], .jobCard"))
                )
            except:
                logger.warning("Timeout waiting for Shine cards")

            # Extract Cards - Try multiple selectors
            job_cards = self.driver.find_elements(By.CSS_SELECTOR, "div[class*='jobCardNova_bigCard']")
            if not job_cards:
                job_cards = self.driver.find_elements(By.CSS_SELECTOR, "div[class*='jobCard']")
            
            if not job_cards:
                 job_cards = self.driver.find_elements(By.CLASS_NAME, "jobCard")

            logger.info(f"Found {len(job_cards)} job cards on Shine")
            if len(job_cards) == 0:
                logger.info(f"Page Title: {self.driver.title}")
                # logger.info(f"Page Source Preview: {self.driver.page_source[:500]}")
            
            for card in job_cards:
                if jobs_found_count >= limit: break
                try:
                    # Title & Link
                    try:
                        title_elem = card.find_element(By.CSS_SELECTOR, "h2 a")
                    except:
                        # Fallback for generic card
                        title_elem = card.find_element(By.TAG_NAME, "a")
                        
                    title_text = title_elem.text.strip()
                    job_url = title_elem.get_attribute("href")
                    if not job_url.startswith("http"):
                        job_url = self.base_url + job_url
                    
                    # Company
                    try:
                        comp_elem = card.find_element(By.CSS_SELECTOR, "div[class*='Company'], .jobCard_jobCard_cName")
                        company_text = comp_elem.text.strip()
                    except:
                        company_text = "Shine Employer"
                        
                    # Location
                    try:
                        loc_elem = card.find_element(By.CSS_SELECTOR, "div[class*='Location'], .jobCard_jobCard_lists_item_location")
                        location_text = loc_elem.text.strip()
                    except:
                        location_text = location

                    job_data = {
                        "title": title_text,
                        "company": company_text,
                        "location": location_text,
                        "url": job_url,
                        "source": "Shine"
                    }
                    
                    if self.save_job(job_data):
                        jobs_found_count += 1
                        
                except Exception as e:
                    logger.warning(f"Error parsing Shine card: {e}")
                    continue
            
            self.update_portal_status("Idle", jobs_found=jobs_found_count)
            logger.info(f"Shine scrape complete. Found {jobs_found_count} new jobs.")
            
        except Exception as e:
            logger.error(f"Shine scrape error: {e}")
            self.update_portal_status("Error")
        finally:
            self.stop_driver()

    def scrape_job_details(self, job_url): pass

class GlassdoorScraper(BaseScraper):
    def __init__(self):
        super().__init__("Glassdoor")
        self.base_url = "https://www.glassdoor.com"

    def search_jobs(self, keywords, location, limit=20):
        self.start_driver()
        jobs_found_count = 0
        try:
            self.update_portal_status("Scraping")
            
            # URL Construction
            # Using generic search URL
            import urllib.parse
            q = urllib.parse.quote(keywords)
            l = urllib.parse.quote(location)
            # This is a common pattern, might redirect to regional site (co.in) automatically
            url = f"{self.base_url}/Job/jobs.htm?sc.keyword={q}&locT=C&locId=0&locKeyword={l}"
            
            logger.info(f"Navigating to {url}")
            self.driver.get(url)
            random_sleep(5, 8) # Longer wait for Glassdoor
            
            # Anti-bot Check
            if "Cloudflare" in self.driver.title or "Just a moment" in self.driver.title:
                logger.error("Glassdoor Blocked by Cloudflare. Aborting.")
                self.update_portal_status("Blocked")
                return

            # Handle "Never Miss an Opportunity" / Login Modal
            try:
                # Close button often has 'Close' text or specific class
                cross_btn = self.driver.find_element(By.CSS_SELECTOR, "button.CloseButton, span.SVGInline.modal_closeIcon, .modal_closeIcon")
                cross_btn.click()
                logger.info("Dismissed Glassdoor modal")
                random_sleep(1, 2)
            except:
                pass

            # Wait for content
            try:
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "li[class*='JobsList_jobListItem']"))
                )
            except:
                logger.warning("Timeout waiting for Glassdoor cards")

            # Extract Cards
            # Selector: li[class*="JobsList_jobListItem"]
            job_cards = self.driver.find_elements(By.CSS_SELECTOR, "li[class*='JobsList_jobListItem']")
            logger.info(f"Found {len(job_cards)} job cards on Glassdoor")
            
            for card in job_cards:
                if jobs_found_count >= limit: break
                try:
                    # Title
                    try:
                        title_elem = card.find_element(By.CSS_SELECTOR, "a[data-test='job-title']")
                        title_text = title_elem.text.strip()
                        job_url = title_elem.get_attribute("href")
                    except:
                        continue # Title is essential

                    # Company
                    try:
                        comp_elem = card.find_element(By.CSS_SELECTOR, "span[class*='EmployerProfile_compactEmployerName'], div[class*='EmployerProfile_employerName']")
                        company_text = comp_elem.text.strip()
                    except:
                        company_text = "Unknown Company"
                        
                    # Location
                    try:
                        loc_elem = card.find_element(By.CSS_SELECTOR, "div[class*='JobCard_location'], div[data-test='location']")
                        location_text = loc_elem.text.strip()
                    except:
                        location_text = location
                    
                    if not job_url.startswith("http"):
                        job_url = self.base_url + job_url

                    job_data = {
                        "title": title_text,
                        "company": company_text,
                        "location": location_text,
                        "url": job_url,
                        "source": "Glassdoor"
                    }
                    
                    if self.save_job(job_data):
                        jobs_found_count += 1
                        
                except Exception as e:
                    logger.warning(f"Error parsing Glassdoor card: {e}")
                    continue
            
            self.update_portal_status("Idle", jobs_found=jobs_found_count)
            logger.info(f"Glassdoor scrape complete. Found {jobs_found_count} new jobs.")

        except Exception as e:
            logger.error(f"Glassdoor scrape error: {e}")
            self.update_portal_status("Error")
        finally:
            self.stop_driver()
    def scrape_job_details(self, job_url): pass

class FounditScraper(BaseScraper):
    def __init__(self):
        super().__init__("Foundit")
        self.base_url = "https://www.foundit.in"
        
    def search_jobs(self, keywords, location, limit=20):
        self.start_driver()
        jobs_found_count = 0
        try:
            self.update_portal_status("Scraping")
            
            # URL Structure: https://www.foundit.in/srp/results?query=Python+Developer&locations=Bangalore
            # Keywords need standard URL encoding or plus for spaces
            import urllib.parse
            q = urllib.parse.quote(keywords)
            l = urllib.parse.quote(location)
            url = f"{self.base_url}/srp/results?query={q}&locations={l}"
            
            logger.info(f"Navigating to {url}")
            self.driver.get(url)
            random_sleep(3, 5)
            
            # Wait for content
            try:
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".cardContainer, .srpCard"))
                )
            except:
                logger.warning("Timeout waiting for Foundit cards")
            
            # Extract Cards
            # .cardContainer seems to be the main wrapper
            job_cards = self.driver.find_elements(By.CSS_SELECTOR, ".cardContainer")
            if not job_cards:
                 job_cards = self.driver.find_elements(By.CLASS_NAME, "srpResultCard")
                 
            logger.info(f"Found {len(job_cards)} job cards on Foundit")
            
            for card in job_cards:
                if jobs_found_count >= limit: break
                try:
                    # Title
                    try:
                        title_elem = card.find_element(By.CSS_SELECTOR, ".jobTitle")
                        title_text = title_elem.text.strip()
                    except:
                        title_text = "Unknown Role"
                        
                    # Company
                    try:
                        comp_elem = card.find_element(By.CSS_SELECTOR, ".companyName")
                        company_text = comp_elem.text.strip()
                    except:
                        company_text = "Unknown Company"
                        
                    # Location
                    try:
                        loc_elem = card.find_element(By.CSS_SELECTOR, ".location")
                        location_text = loc_elem.text.strip()
                    except:
                        location_text = location

                    # Link Logic
                    # It's an SPA, so we might need to construct it or find the hidden link
                    # Attempt 1: Look for any 'a' tag
                    try:
                        # Often the title is a link
                        link_elem = card.find_element(By.TAG_NAME, "a")
                        job_url = link_elem.get_attribute("href")
                        
                        # Verify quality of link
                        if "javascript" in job_url or not job_url.startswith("http"):
                            # Attempt 2: Construct from ID
                            card_id = card.get_attribute("data-jobid") or card.get_attribute("id")
                            if card_id:
                                # clean id if needed (sometimes 'card_123')
                                clean_id = ''.join(filter(str.isdigit, card_id))
                                if clean_id:
                                    job_url = f"{self.base_url}/job-description/{clean_id}"
                    except:
                        job_url = self.base_url

                    job_data = {
                        "title": title_text,
                        "company": company_text,
                        "location": location_text,
                        "url": job_url,
                        "source": "Foundit"
                    }
                    
                    if self.save_job(job_data):
                        jobs_found_count += 1
                        
                except Exception as e:
                    logger.warning(f"Error parsing Foundit card: {e}")
                    continue
            
            self.update_portal_status("Idle", jobs_found=jobs_found_count)
            logger.info(f"Foundit scrape complete. Found {jobs_found_count} new jobs.")
            
        except Exception as e:
            logger.error(f"Foundit scrape error: {e}")
            self.update_portal_status("Error")
        finally:
            self.stop_driver()
    def scrape_job_details(self, job_url): pass

class IntershalaScraper(BaseScraper):
    def __init__(self):
        super().__init__("Intershala")
        self.base_url = "https://internshala.com"

    def search_jobs(self, keywords, location, limit=20):
        self.start_driver()
        jobs_found_count = 0
        try:
            self.update_portal_status("Scraping")
            
            # URL Structure: https://internshala.com/jobs/keywords-python%20developer/
            # Location is filter based, but keywords usually suffice for URL
            # We can append location to keywords if needed or use filter params
            # For simplicity, search keywords globally then let user filter or rely on keywords
            q = keywords.replace(" ", "%20")
            url = f"{self.base_url}/jobs/keywords-{q}/"
            
            logger.info(f"Navigating to {url}")
            self.driver.get(url)
            random_sleep(3, 5)
            
            # Handle Modal - "Sign up now to unlock"
            try:
                # Common modal close button
                modal_close = self.driver.find_element(By.CSS_SELECTOR, "#close_popup, .modal-close, .close-modal")
                modal_close.click()
                logger.info("Dismissed Internshala modal")
                random_sleep(1, 2)
            except:
                pass # No modal or different selector

            # Wait for cards
            try:
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".individual_internship"))
                )
            except:
                logger.warning("Timeout waiting for Internshala cards")
            
            job_cards = self.driver.find_elements(By.CSS_SELECTOR, ".individual_internship")
            logger.info(f"Found {len(job_cards)} job cards on Internshala")
            
            for card in job_cards:
                if jobs_found_count >= limit: break
                try:
                    # Title & Link
                    title_text = ""
                    job_url = ""
                    try:
                        # Try multiple selectors for title/link
                        title_elem = None
                        for sel in [".job-title-href", ".profile", ".heading_4_5 a"]:
                            try:
                                title_elem = card.find_element(By.CSS_SELECTOR, sel)
                                if title_elem.text.strip():
                                    break
                            except: continue
                        
                        if title_elem:
                            title_text = title_elem.text.strip()
                            job_url = title_elem.get_attribute("href")
                            if job_url and not job_url.startswith("http"):
                                job_url = self.base_url + job_url
                    except:
                        pass

                    if not title_text:
                        # Fallback: Parse from data-href
                        data_href = card.get_attribute("data-href")
                        if data_href:
                            job_url = self.base_url + data_href if not data_href.startswith("http") else data_href
                            # Try to extract title from URL part: /job/detail/title-slug
                            try:
                                slug = data_href.split("/")[-1]
                                # Remove -job-in-location-at-company...
                                # This is heuristic, but better than nothing
                                clean_slug = slug.split("-job-in-")[0]
                                title_text = clean_slug.replace("-", " ").title()
                            except:
                                title_text = "Internshala Job" # Only if absolutely failed
                    
                    if not title_text:
                         # Try generic h3
                         try:
                             title_elem = card.find_element(By.TAG_NAME, "h3")
                             title_text = title_elem.text.strip()
                         except: pass

                    if not title_text:
                        # logger.warning(f"Skipping card due to empty title. HTML snippet: {card.get_attribute('outerHTML')[:300]}")
                        continue # Skip if no title found

                    # Company
                    company_text = "Unknown Company"
                    try:
                        for sel in [".company-name", ".link_display_name", ".company_and_premium"]:
                            try:
                                comp_elem = card.find_element(By.CSS_SELECTOR, sel)
                                txt = comp_elem.text.strip()
                                if txt:
                                    company_text = txt
                                    break
                            except: continue
                    except: pass
                    
                    # Location
                    location_text = location
                    try:
                        for sel in [".location", ".location_link", "#location_names"]:
                            try:
                                loc_elem = card.find_element(By.CSS_SELECTOR, sel)
                                txt = loc_elem.text.strip()
                                if txt:
                                    location_text = txt
                                    break
                            except: continue
                    except: pass
                        
                    job_data = {
                        "title": title_text,
                        "company": company_text,
                        "location": location_text,
                        "url": job_url,
                        "source": "Intershala"
                    }
                    
                    if self.save_job(job_data):
                        jobs_found_count += 1
                        
                except Exception as e:
                    logger.warning(f"Error parsing Internshala card: {e}")
                    continue
            
            self.update_portal_status("Idle", jobs_found=jobs_found_count)
            logger.info(f"Internshala scrape complete. Found {jobs_found_count} new jobs.")

        except Exception as e:
            logger.error(f"Internshala scrape error: {e}")
            self.update_portal_status("Error")
        finally:
            self.stop_driver()
    def scrape_job_details(self, job_url): pass

class IIMJobsScraper(BaseScraper):
    def __init__(self):
        super().__init__("IIMJobs")
        self.base_url = "https://www.iimjobs.com"
        
    def search_jobs(self, keywords, location, limit=20):
        self.start_driver()
        jobs_found_count = 0
        try:
            self.update_portal_status("Scraping")
            
            # URL Structure: https://www.iimjobs.com/search/product-manager-jobs?loc=Bangalore
            # Keywords need to be hyphenated
            kw = keywords.replace(" ", "-")
            url = f"{self.base_url}/search/{kw}-jobs?loc={location}"
            
            logger.info(f"Navigating to {url}")
            self.driver.get(url)
            random_sleep(3, 5)
            
            # Wait for content
            try:
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".joblist-card-v2, div[class*='joblist-card']"))
                )
            except:
                logger.warning("Timeout waiting for IIMJobs cards")
            
            # Extract Cards
            # The class name might be dynamic Mui, so we look for the semantic container we found or generic structure
            job_cards = self.driver.find_elements(By.CSS_SELECTOR, ".joblist-card-v2")
            if not job_cards:
                 job_cards = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'joblist-card')]")
                 
            logger.info(f"Found {len(job_cards)} job cards on IIMJobs")
            
            for card in job_cards:
                if jobs_found_count >= limit: break
                try:
                    # Link is usually the wrapping anchor or first anchor
                    link_elem = card.find_element(By.TAG_NAME, "a")
                    job_url = link_elem.get_attribute("href")
                    
                    # Title & Company logic based on inspection
                    # Often "Company - Title" in one line, or separate
                    text_content = card.text.split('\n')
                    
                    # Heuristic parsing of text content
                    # [0] might be "Premium", [1] Title, [2] Company, etc.
                    # Let's try to find bold text for Title
                    
                    title_text = "Unknown Role"
                    company_text = "Unknown Company"
                    
                    # Try specific selectors if available
                    try: 
                        # Assuming title is in an anchor or h tag, but often it's just styled text
                        # Based on inspection: <p class="MuiTypography-subtitle2">Company - Title</p>
                        # Let's try to find that pattern
                        header_elem = card.find_element(By.XPATH, ".//p[contains(@class, 'subtitle2')] | .//span[contains(@class, 'subtitle2')]")
                        header_text = header_elem.text
                        if "-" in header_text:
                            parts = header_text.split("-", 1)
                            company_text = parts[0].strip()
                            title_text = parts[1].strip()
                        else:
                            title_text = header_text
                    except:
                        # Fallback: Use the first non-empty text lines
                        if len(text_content) > 0: title_text = text_content[0]
                        if len(text_content) > 1: company_text = text_content[1]
                        
                    # Location
                    location_text = location 
                    try:
                        # Look for location icon or text row
                        # Using the search location as default fallback
                        loc_elem = card.find_element(By.XPATH, ".//p[contains(@class, 'subtitle3')] | .//span[contains(@class, 'subtitle3')][contains(text(), ',') or contains(text(), 'India')]")
                        location_text = loc_elem.text
                    except: pass

                    job_data = {
                        "title": title_text,
                        "company": company_text,
                        "location": location_text,
                        "url": job_url,
                        "source": "IIMJobs"
                    }
                    
                    if self.save_job(job_data):
                        jobs_found_count += 1
                        
                except Exception as e:
                    logger.warning(f"Error parsing IIMJobs card: {e}")
                    continue
            
            self.update_portal_status("Idle", jobs_found=jobs_found_count)
            logger.info(f"IIMJobs scrape complete. Found {jobs_found_count} new jobs.")
            
        except Exception as e:
            logger.error(f"IIMJobs scrape error: {e}")
            self.update_portal_status("Error")
        finally:
            self.stop_driver()

    def scrape_job_details(self, job_url): pass

class FreshersworldScraper(BaseScraper):
    def __init__(self):
        super().__init__("Freshersworld")
        self.base_url = "https://www.freshersworld.com"

    def search_jobs(self, keywords, location, limit=20):
        self.start_driver()
        jobs_found_count = 0
        try:
            self.update_portal_status("Scraping")
            
            # URL Structure: https://www.freshersworld.com/jobs/jobsearch/python-developer-jobs-in-bangalore
            # Slugify keywords and location
            k_slug = keywords.lower().replace(" ", "-")
            l_slug = location.lower().replace(" ", "-") if location else "india"
            
            # Construct URL
            url = f"{self.base_url}/jobs/jobsearch/{k_slug}-jobs-in-{l_slug}"
            
            logger.info(f"Navigating to {url}")
            self.driver.get(url)
            random_sleep(3, 5)
            
            # Handle "Jobseeker Login" Modal
            try:
                # Common modal close buttons
                modal_close = self.driver.find_element(By.CSS_SELECTOR, "#login_modal_close, .close-modal, .modal-close, button.close")
                if modal_close.is_displayed():
                    modal_close.click()
                    logger.info("Dismissed Freshersworld modal")
                    random_sleep(1, 2)
            except:
                pass 

            # Wait for cards
            try:
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".job-container"))
                )
            except:
                logger.warning("Timeout waiting for Freshersworld cards")
            
            job_cards = self.driver.find_elements(By.CSS_SELECTOR, ".job-container")
            logger.info(f"Found {len(job_cards)} job cards on Freshersworld")
            
            for card in job_cards:
                if jobs_found_count >= limit: break
                try:
                    # Title
                    try:
                        title_elem = card.find_element(By.CSS_SELECTOR, ".seo_title, .job-title, span[class*='title']")
                        title_text = title_elem.text.strip()
                    except:
                        title_text = "Unknown Role"

                    # Company
                    try:
                        comp_elem = card.find_element(By.CSS_SELECTOR, ".company-name, .latest-jobs-title")
                        company_text = comp_elem.text.strip()
                    except:
                        company_text = "Unknown Company"
                    
                    # Location
                    try:
                        loc_elem = card.find_element(By.CSS_SELECTOR, ".job-location, .job-location-name")
                        location_text = loc_elem.text.strip()
                    except:
                        location_text = location 
                    
                    # Link
                    # Often the title is a link or there's a specific 'Apply' button
                    try:
                        link_elem = card.find_element(By.CSS_SELECTOR, ".view-apply-button a, a.job-title-link") # heuristic
                        job_url = link_elem.get_attribute("href")
                        if not job_url:
                             # Fallback: finding first link in card
                             job_url = card.find_element(By.TAG_NAME, "a").get_attribute("href")
                    except:
                        try: 
                             job_url = card.find_element(By.TAG_NAME, "a").get_attribute("href")
                        except:
                             job_url = self.base_url

                    if not job_url.startswith("http"):
                        job_url = self.base_url + job_url

                    job_data = {
                        "title": title_text,
                        "company": company_text,
                        "location": location_text,
                        "url": job_url,
                        "source": "Freshersworld"
                    }
                    
                    if self.save_job(job_data):
                        jobs_found_count += 1
                        
                except Exception as e:
                    logger.warning(f"Error parsing Freshersworld card: {e}")
                    continue
            
            self.update_portal_status("Idle", jobs_found=jobs_found_count)
            logger.info(f"Freshersworld scrape complete. Found {jobs_found_count} new jobs.")

        except Exception as e:
            logger.error(f"Freshersworld scrape error: {e}")
            self.update_portal_status("Error")
        finally:
            self.stop_driver()
    def scrape_job_details(self, job_url): pass

class WellfoundScraper(BaseScraper):
    def __init__(self):
        super().__init__("Wellfound")
        self.base_url = "https://wellfound.com"

    def search_jobs(self, keywords, location, limit=20):
        self.start_driver()
        jobs_found_count = 0
        try:
            self.update_portal_status("Scraping")
            
            # URL Construction
            # Pattern: https://wellfound.com/role/l/python-developer/bangalore-urban
            # We need to slugify carefully
            role_slug = keywords.lower().replace(" ", "-")
            
            # Location slug is tricky, usually ends with '-urban' for cities or just the city name
            # Let's try basic slug first.
            loc_slug = location.lower().replace(" ", "-")
            if "bangalore" in loc_slug and "urban" not in loc_slug:
                loc_slug += "-urban" # Common Wellfound pattern for Bangalore
            
            url = f"{self.base_url}/role/l/{role_slug}/{loc_slug}"
            
            logger.info(f"Navigating to {url}")
            self.driver.get(url)
            random_sleep(3, 5)
            
            # Anti-bot / Cloudflare Check
            if "Cloudflare" in self.driver.title:
                logger.error("Wellfound Blocked by Cloudflare. Aborting.")
                self.update_portal_status("Blocked")
                return

            # Handle "Never Miss" / Login Modal if it appears
            try:
                # Heuristic for close button
                modal_close = self.driver.find_element(By.CSS_SELECTOR, "[data-test='ModalClose'], button[aria-label='Close']")
                modal_close.click()
                logger.info("Dismissed Wellfound modal")
                random_sleep(1, 2)
            except:
                pass

            # Wait for cards
            try:
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                # Try data-test first (more stable)
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-test='JobResult'], div[class*='styles_result']"))
                )
            except:
                logger.warning("Timeout waiting for Wellfound cards")

            # Extract Cards
            # Selector: div[data-test="JobResult"] is best if available
            job_cards = self.driver.find_elements(By.CSS_SELECTOR, "div[data-test='JobResult']")
            if not job_cards:
                 # Subagent found: .mb-6.w-full.rounded.border.border-gray-400.bg-white
                 job_cards = self.driver.find_elements(By.CSS_SELECTOR, "div.mb-6.w-full.rounded.border")
                 if not job_cards:
                     job_cards = self.driver.find_elements(By.CSS_SELECTOR, "div.bg-white.rounded.border")

            logger.info(f"Found {len(job_cards)} job cards on Wellfound")
            
            for card in job_cards:
                if jobs_found_count >= limit: break
                try:
                    # Title
                    # Inspection: a.text-brand-burgandy or look for h2
                    try:
                        title_elem = card.find_element(By.CSS_SELECTOR, "a[class*='text-brand-burgandy'], a[href*='/jobs/']")
                        title_text = title_elem.text.strip()
                        job_url = title_elem.get_attribute("href")
                    except:
                         # Fallback for title
                        try:
                             title_elem = card.find_elements(By.TAG_NAME, "a")[0]
                             title_text = title_elem.text.strip()
                             job_url = title_elem.get_attribute("href")
                        except: continue

                    # Company
                    # Inspection: h2
                    try:
                        comp_elem = card.find_element(By.TAG_NAME, "h2")
                        company_text = comp_elem.text.strip()
                    except:
                        company_text = "Wellfound Company"
                        
                    # Location
                    location_text = location
                    try:
                        # Try finding elements with location-like text
                        text_elems = card.find_elements(By.CSS_SELECTOR, "span, div")
                        for el in text_elems:
                            txt = el.text.strip()
                            if "remote" in txt.lower() or "india" in txt.lower() or location.lower() in txt.lower():
                                location_text = txt
                                break
                    except:
                        pass
                    
                    if not job_url.startswith("http"):
                        job_url = self.base_url + job_url

                    job_data = {
                        "title": title_text,
                        "company": company_text,
                        "location": location_text,
                        "url": job_url,
                        "source": "Wellfound"
                    }
                    
                    if self.save_job(job_data):
                        jobs_found_count += 1
                        
                except Exception as e:
                    logger.warning(f"Error parsing Wellfound card: {e}")
                    continue
            
            self.update_portal_status("Idle", jobs_found=jobs_found_count)
            logger.info(f"Wellfound scrape complete. Found {jobs_found_count} new jobs.")

        except Exception as e:
            logger.error(f"Wellfound scrape error: {e}")
            self.update_portal_status("Error")
        finally:
            self.stop_driver()
    def scrape_job_details(self, job_url): pass

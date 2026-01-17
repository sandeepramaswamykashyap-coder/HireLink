from backend.utils.selenium_utils import setup_driver, random_sleep
from backend.database import get_db, Job, Resume, Application
from sqlalchemy import func
from backend.utils.logger import logger
from backend.agents.cover_letter_generator import CoverLetterGenerator
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from datetime import datetime
import os

class AutoApplier:
    def __init__(self):
        self.cl_gen = CoverLetterGenerator()
        self.driver = None
        
    def enrich_jobs_data(self, days_lookback=2):
        """
        Scans recent jobs for missing descriptions and scrapes them.
        """
        from backend.database import SessionLocal, Job
        from backend.scrapers.linkedin import LinkedInScraper
        from datetime import datetime, timedelta
        
        db = SessionLocal()
        try:
            # Find jobs with "See Link" or very short descriptions
            cutoff = datetime.utcnow() - timedelta(days=days_lookback)
            
            jobs_to_fix = db.query(Job).filter(
                Job.scraped_date >= cutoff,
                (Job.description == "See Link") | (func.length(Job.description) < 150)
            ).all()
            
            if not jobs_to_fix: return
            
            logger.info(f"Found {len(jobs_to_fix)} jobs requiring data enrichment.")
            
            # Group by portal to reuse scrapers? For now just handle LinkedIn
            linkedin_scraper = None
            
            for job in jobs_to_fix:
                if job.source == "LinkedIn":
                    if not linkedin_scraper: linkedin_scraper = LinkedInScraper()
                    
                    details = linkedin_scraper.scrape_job_details(job.url)
                    if details and len(details.get("description", "")) > 100:
                         job.description = details['description']
                         if details.get('skills'):
                             job.skills = str(details['skills'])
                         db.commit()
                         logger.info(f"Enriched job {job.id}: {job.title}")
            
            if linkedin_scraper: linkedin_scraper.stop_driver()
            
        except Exception as e:
            logger.error(f"Enrichment failed: {e}")
        finally:
            db.close()

    def build_candidate_profile(self, user_id, resume_id):
        """
        Constructs a Holistic Pilot Profile for the AI.
        Merges Resume Structure + Smart Answers + User Preferences.
        """
        from backend.database import SessionLocal, Resume, QuestionAnswer, AppUser
        db = SessionLocal()
        try:
            # 1. Fetch Core Entities
            user = db.query(AppUser).filter_by(id=user_id).first()
            resume = db.query(Resume).filter_by(id=resume_id).first()
            # FIX: STRICT DATA ISOLATION
            qa_list = db.query(QuestionAnswer).filter_by(user_id=user_id).all()
            
            if not user or not resume: return None
            
            # 2. Base Profile from Resume (Structured)
            profile = resume.parsed_data if resume.parsed_data else {}
            
            # Ensure Core Contact Info is present (Resume parsing might fail)
            contact = profile.get("contact", {})
            if not contact.get("email"): contact["email"] = user.email or resume.email
            if not contact.get("phone"): contact["phone"] = resume.phone
            if not contact.get("name"): contact["name"] = user.name or resume.name
            profile["contact"] = contact
            
            # 4. Flatten Current Experience for easier LLM access
            if profile.get("experience") and isinstance(profile["experience"], list) and len(profile["experience"]) > 0:
                latest = profile["experience"][0]
                profile["current_role"] = latest.get("role", "") or latest.get("title", "")
                profile["current_company"] = latest.get("company", "") or latest.get("employer", "")
                profile["current_summary"] = latest.get("description", "")
            
            # 5. Smart Answers (The "Knowledge Base")
            # Group by category for cleaner LLM context
            knowledge_base = {}
            for qa in qa_list:
                if qa.answer:
                    if qa.category not in knowledge_base: knowledge_base[qa.category] = {}
                    knowledge_base[qa.category][qa.question] = qa.answer
            
            profile["smart_answers"] = knowledge_base
            
            # 6. User Preferences (The "Mission")
            profile["preferences"] = {
                "target_roles": user.target_roles,
                "target_cities": user.target_cities,
                "work_mode": user.work_mode,
                "salary_expectations": user.instructions # Or specific field if we had one
            }
            
            return profile
            
        finally:
            db.close()
        
    def start_browser(self):
        if not self.driver:
            logger.info("Starting AutoApplier browser session (Visible)...")
            self.driver = setup_driver(headless=False, detach=False)
            
    def _click_radio(self, parent, value_text):
        """Helper to click Yes/No radio buttons"""
        try:
            # Find label containing text
            labels = parent.find_elements(By.TAG_NAME, "label")
            for lbl in labels:
                if value_text.lower() in lbl.text.lower():
                    lbl.click()
                    return
        except: pass

    def close_browser(self):
        if self.driver:
            logger.info("Closing AutoApplier browser session...")
            self.driver.quit()
            self.driver = None

    def verify_portal_login(self, portal_name):
        """Checks if the user is authenticated on a given portal"""
        portal_name = portal_name.lower()
        try:
            if not self.driver: self.start_browser()
            
            # 1. Check for common "Not Logged In" indicators across all sites
            # If we see a login form, we are definitely NOT logged in
            login_indicators = [
                "//input[@type='password']",
                "//input[@name='password']",
                "//button[contains(text(), 'Sign in')]",
                "//button[contains(text(), 'Login')]"
            ]
            
            if "linkedin" in portal_name:
                self.driver.get("https://www.linkedin.com/feed/")
                random_sleep(3, 4)
                if "login" in self.driver.current_url or "checkpoint" in self.driver.current_url: return False
                # Active session has global nav me photo
                return len(self.driver.find_elements(By.CLASS_NAME, "global-nav__me-photo")) > 0 or \
                       len(self.driver.find_elements(By.ID, "global-nav-typeahead")) > 0
            
            elif "naukri" in portal_name:
                self.driver.get("https://www.naukri.com/mnjuser/profile")
                random_sleep(3, 4)
                if "login" in self.driver.current_url: return False
                # If we are logged in, we should see the profile page or dashboard
                return "profile" in self.driver.current_url.lower() or "dashboard" in self.driver.current_url.lower()
            
            elif "indeed" in portal_name:
                self.driver.get("https://www.indeed.com/")
                random_sleep(3, 4)
                if "login" in self.driver.current_url: return False
                return len(self.driver.find_elements(By.CSS_SELECTOR, "a[href*='notifications']")) > 0 or \
                       len(self.driver.find_elements(By.CSS_SELECTOR, "div[class*='AccountMenu']")) > 0
            
            elif "shine" in portal_name:
                self.driver.get("https://www.shine.com/myshine/dashboard/")
                random_sleep(3, 4)
                if "login" in self.driver.current_url.lower(): return False
                return "dashboard" in self.driver.current_url.lower()

            elif "foundit" in portal_name:
                self.driver.get("https://www.foundit.in/login")
                random_sleep(3, 4)
                # redirected away from login means success
                return "login" not in self.driver.current_url.lower()

            elif "internshala" in portal_name:
                self.driver.get("https://internshala.com/student/dashboard")
                random_sleep(3, 4)
                if "login" in self.driver.current_url.lower(): return False
                return "dashboard" in self.driver.current_url.lower()

            elif "iimjobs" in portal_name:
                self.driver.get("https://www.iimjobs.com/dashboard")
                random_sleep(3, 4)
                return "login" not in self.driver.current_url.lower() and "dashboard" in self.driver.current_url.lower()

            elif "wellfound" in portal_name:
                self.driver.get("https://wellfound.com/jobs")
                random_sleep(3, 4)
                if "login" in self.driver.current_url.lower(): return False
                return len(self.driver.find_elements(By.CSS_SELECTOR, "[class*='avatar']")) > 0 or \
                       len(self.driver.find_elements(By.CSS_SELECTOR, "a[href*='settings']")) > 0
            
            # Safety Check: If we see a password field, we are definitely NOT logged in
            if len(self.driver.find_elements(By.XPATH, "//input[@type='password']")) > 0:
                return False

            # Default to False for safety
            return False
        except RuntimeError as re:
            raise re
        except Exception as e:
            logger.error(f"Error checking {portal_name} login: {e}")
            return False

    def check_all_portal_logins(self, portals):
        """Batch check logins for a list of portals"""
        results = {}
        for p in portals:
            results[p] = self.verify_portal_login(p)
        return results

    def launch_portals_for_login(self):
        """Opens login pages for all major portals in separate tabs"""
        urls = {
            "LinkedIn": "https://www.linkedin.com/login",
            "Naukri": "https://www.naukri.com/nlogin/login",
            "Indeed": "https://secure.indeed.com/auth",
            "Shine": "https://www.shine.com/myshine/login/",
            "Foundit": "https://www.foundit.in/login",
            "Internshala": "https://internshala.com/login/user",
            "IIMJobs": "https://www.iimjobs.com/login",
            "Freshersworld": "https://www.freshersworld.com/user/login",
            "Wellfound": "https://wellfound.com/login",
            "Glassdoor": "https://www.glassdoor.co.in/profile/login_input.htm"
        }
        
        if not self.driver: self.start_browser()
        
        # Open first one normally
        first_portal = list(urls.keys())[0]
        self.driver.get(urls[first_portal])
        
        # Open others in new tabs
        for name, url in list(urls.items())[1:]:
            self.driver.execute_script(f"window.open('{url}', '_blank');")
            random_sleep(1, 2)
        
        logger.info("Launched all portals for login.")

    def attempt_portal_login(self, portal_name):
        """
        Attempts to log in to a portal using stored credentials.
        """
        from backend.database import SessionLocal, PortalCredential
        from selenium.webdriver.common.keys import Keys
        
        db = SessionLocal()
        try:
            creds = db.query(PortalCredential).filter_by(portal_name=portal_name).first()
            if not creds:
                logger.warning(f"No credentials found for {portal_name}")
                return False
                
            logger.info(f"Attempting auto-login for {portal_name} with user {creds.username}")
            
            # Login URLs & Selectors
            login_configs = {
                "LinkedIn": {
                    "url": "https://www.linkedin.com/login",
                    "user_sel": "#username",
                    "pass_sel": "#password",
                    "btn_sel": "button[type='submit']"
                },
                "Indeed": {
                    "url": "https://secure.indeed.com/auth",
                    "user_sel": "input[name='__email']", # Indeed is multi-step usually, this is basic 
                    "pass_sel": "input[name='__password']",
                    "btn_sel": "button[type='submit']"
                },
                "Naukri": {
                    "url": "https://www.naukri.com/nlogin/login",
                    "user_sel": "#usernameField",
                    "pass_sel": "#passwordField",
                    "btn_sel": "button[type='submit']"
                },
                 "Internshala": {
                    "url": "https://internshala.com/login/user",
                    "user_sel": "#email",
                    "pass_sel": "#password",
                    "btn_sel": "#login_submit"
                }
            }
            
            config = login_configs.get(portal_name)
            if not config: return False # Not supported for auto-login yet
            
            if not self.driver: self.start_browser()
            
            self.driver.get(config["url"])
            random_sleep(2, 4)
            
            # Fill Username
            try:
                u_elem = self.driver.find_element(By.CSS_SELECTOR, config['user_sel'])
                u_elem.clear()
                u_elem.send_keys(creds.username)
                random_sleep(1)
            except: return False
            
            # Fill Password (if present on same page)
            try:
                p_elem = self.driver.find_element(By.CSS_SELECTOR, config['pass_sel'])
                p_elem.clear()
                p_elem.send_keys(creds.password)
                random_sleep(1)
                
                # Click Login
                b_elem = self.driver.find_element(By.CSS_SELECTOR, config['btn_sel'])
                b_elem.click()
                
                random_sleep(5, 8)
                
                # Verify Success
                if self.verify_portal_login(portal_name):
                    return True
            except:
                pass
                
            return False
            
        except Exception as e:
            logger.error(f"Auto-login failed for {portal_name}: {e}")
            return False
        finally:
            db.close()

    def run_hyper_automation(self, keywords, location, resume_id, target_portals=None, user_email=None):
        """
        Unified 'One-Click' engine:
        1. Verifies logins for SELECTED portals.
        2. Scrapes new jobs matching keywords/location for LOGGED IN portals only.
        3. Matches these jobs against the selected resume.
        4. Automatically applies to the best matches.
        5. Sends an email report if user_email is provided.
        """
        from backend.utils.scraper_utils import run_scraper
        from backend.agents.job_matcher import JobMatcher
        from backend.utils.notifier import EmailNotifier
        
        # Session Logging
        session_logs = []
        
        # IMMEDIATE FEEDBACK
        yield {"step": "Initiating", "status": "Hyper-Drive Engines Spooling Up...", "progress": 5}
        
        yield {"step": "Login Verification", "status": "Checking Portal Access...", "progress": 10}
        
        # User selected portals > Hardcoded Default
        portals = target_portals if target_portals else ["LinkedIn", "Naukri", "Indeed", "Shine", "Foundit", "Internshala", "IIMJobs", "Wellfound"]
        
        active_portals = []
        try:
            login_results = self.check_all_portal_logins(portals)
            
            for p, is_logged_in in login_results.items():
                if is_logged_in:
                    active_portals.append(p)
                else:
                    # TRY AUTO-LOGIN
                    yield {"step": "Auto-Login", "status": f"Session expired for {p}. Attempting Auto-Login...", "progress": 15}
                    try:
                        if self.attempt_portal_login(p):
                            yield {"step": "Auto-Login", "status": f"Successfully logged into {p}! ✅", "progress": 20}
                            active_portals.append(p)
                        else:
                            yield {"step": "Auto-Login", "status": f"Could not log into {p}. Skipping.", "progress": 20}
                    except Exception as e:
                         logger.error(f"Auto-login failed for {p}: {e}")

            # Fallback Logic
            if not active_portals:
                yield {"step": "Warning", "status": "Login verification failed. Attempting public scrape mode...", "progress": 25}
                active_portals = portals 
            else:
                yield {"step": "Login Success", "status": f"Active Sessions: {', '.join(active_portals)}", "progress": 25}

        except Exception as e:
             logger.error(f"Login Check Critical Fail: {e}")
             yield {"step": "Error", "status": "Login Verification System Failed. Proceeding with caution...", "progress": 25}
             active_portals = portals # Hope for best

        # --- RELEASE BROWSER FOR SCRAPERS ---
        self.close_browser()

        yield {"step": "Scraping Jobs", "status": f"Scraping {', '.join(active_portals)}...", "progress": 30}
        new_jobs_count = run_scraper(active_portals, keywords, location)
        
        # --- ENRICHMENT STEP ---
        yield {"step": "Enrichment", "status": "Verifying job data quality...", "progress": 40}
        self.enrich_jobs_data(days_lookback=2)

        yield {"step": "Matching Jobs", "status": f"Found {new_jobs_count} new. Calculating match scores...", "progress": 60}
        matcher = JobMatcher()
        matches = matcher.match_jobs(resume_id, limit=20) # Limit hyper-apply to top 20 for safety
        
        if not matches:
            yield {"step": "Completed", "status": "No eligible new jobs found to apply for.", "progress": 100}
            return

        total_matches = len(matches)
        yield {"step": "Applying", "status": f"Applying to {total_matches} best matches...", "progress": 80}
        success_count = 0
        for i, match in enumerate(matches):
            job = match['job']
            yield {"step": "Applying", "status": f"[{i+1}/{total_matches}] Applying to {job.title} @ {job.company}...", "progress": 80 + int(((i+1)/total_matches)*19)}
            try:
                # Use lambda to emit status updates via yield
                # STEP 1: Call _apply_to_job_gen which I will define below.
                success = False
                final_status_msg = "Failed" # Default
                
                for msg in self._apply_to_job_gen(job.id, resume_id):
                    yield {"step": "Applying", "status": msg, "progress": 80 + int(((i+1)/total_matches)*19)}
                    if msg == "SUCCESS": 
                        success = True
                        final_status_msg = "Success"
                    if msg == "FAILURE":
                        final_status_msg = "Failed"
                
                if success: success_count += 1
                
                session_logs.append({
                    'title': job.title,
                    'company': job.company,
                    'portal': job.source,
                    'status': final_status_msg
                })

            except Exception as e:
                logger.error(f"Hyper-Automation: Failed to apply: {e}")
                session_logs.append({
                    'title': job.title,
                    'company': job.company,
                    'portal': job.source,
                    'status': "Error"
                })
        
        if total_matches == 0:
            yield {"step": "Finished", "status": "No new matching jobs found. All scanned roles were either low-quality or already applied to.", "progress": 100}
        else:
            yield {"step": "Finished", "status": f"Hyper-Automation Mission Concluded. Processed {total_matches} candidates, successfully sent {success_count} applications. 🚀", "progress": 100}
            
            # --- SEND EMAIL REPORT ---
            if user_email and session_logs:
                yield {"step": "Reporting", "status": "Sending session email report...", "progress": 100}
                notifier = EmailNotifier()
                session_data = {
                    'total': total_matches,
                    'success': success_count,
                    'logs': session_logs
                }
                notifier.send_session_report(user_email, session_data)
                yield {"step": "Reporting", "status": "Report Sent! Check your inbox.", "progress": 100}
        
        # --- FINAL CLEANUP ---
        self.close_browser()


    def find_smart_answer(self, label_text):
        """Fuzzy match label text against DB Questions"""
        if not label_text: return None
        label_text = label_text.lower()
        
        # Load QA Cache if empty (Basic caching)
        if not hasattr(self, 'qa_cache'):
            from backend.database import SessionLocal, QuestionAnswer
            db = SessionLocal()
            self.qa_cache = db.query(QuestionAnswer).all()
            db.close()
            
        # 1. Exact/Substring Match
        for qa in self.qa_cache:
            q_text = qa.question.lower()
            if q_text in label_text or label_text in q_text:
                return qa.answer
                
        # 2. Keyword Match (Advanced)
        keywords = {
            "notice": ["notice period", "how soon"],
            "ctc": ["ctc", "salary", "compensation"],
            "experience": ["experience", "years of"],
            "sponsorship": ["sponsorship", "visa"],
            "relocate": ["relocate"],
            "gender": ["gender"]
        }
        
        for key, tokens in keywords.items():
            if any(t in label_text for t in tokens):
                # Find the DB entry for this category/key
                for qa in self.qa_cache:
                    if key in qa.question.lower():
                        return qa.answer
                        
        return None

    def apply_to_job(self, job_id, resume_id, status_callback=None):
        """Legacy Wrapper for compatibility"""
        # Consume the generator and log output, returning final status
        success = False
        for msg in self._apply_to_job_gen(job_id, resume_id):
            if status_callback: status_callback(msg)
            if msg == "SUCCESS": success = True
        return success

    def _apply_to_job_gen(self, job_id, resume_id):
        """
        Generator version of apply_to_job.
        Yields status strings.
        Yields "SUCCESS" or "FAILURE" as last message (imperfect but functional protocol).
        """
        def _log(msg):
             # Helper to yield? No, we are in the generator.
             # We just yield msg.
             pass 

        # We can't use inner function _log to yield. We must yield directly.
        # So we replace _log(...) with yield ...
        
        # ... (Rest of logic copied and adapted) ...
        # Ensure browser is running
        self.start_browser()
        
        from backend.database import SessionLocal
        db = SessionLocal()
        try:
            # 1. Fetch Data
            job = db.query(Job).filter_by(id=job_id).first()
            resume = db.query(Resume).filter_by(id=resume_id).first()
            
            # ... Data Fetching ...
            # ... Data Fetching ...
            # PRIVACY FIX: Filter Smart Answers by User
            from backend.database import QuestionAnswer, AppUser
            
            # Find User via Resume Email (Foreign Key workaround since we don't have direct link yet)
            job_owner = db.query(AppUser).filter(AppUser.email == resume.email).first()
            if job_owner:
                 qa_records = db.query(QuestionAnswer).filter_by(user_id=job_owner.id).all()
            else:
                 # Fallback: Empty or maybe try generic? Safe to return empty.
                 logger.warning(f"Could not link Resume {resume.id} to a User. Skipping Smart Answers.")
                 qa_records = []
                 
            smart_answers = {qa.question: qa.answer for qa in qa_records if qa.answer}
             
            if not job or not resume:
                logger.error("Job or Resume not found in DB")
                yield "Error: Job/Resume not found"
                yield "FAILURE"
                return

            job_data = {'id': job.id, 'title': job.title, 'company': job.company, 'url': job.url}
            
            candidate_profile = self.build_candidate_profile(user_id=1, resume_id=resume.id)
            if not candidate_profile:
                yield "Error: Profile build failed"
                yield "FAILURE" 
                return
                
            resume_data = {'id': resume.id, 'name': resume.name, 'email': resume.email, 'phone': resume.phone}
            
            yield f"Starting application for {job_data['title']}..."
            logger.info(f"Starting application for {job_data['title']}")
            
            # 3. Navigation
            try:
                yield "Navigating to Job URL..."
                logger.info(f"Pilot: Navigating to {job_data['url']}")
                self.driver.get(job_data['url'])
                random_sleep(3, 5)
                
                # Enhanced Logic: Click "Easy Apply"
                quick_hunt_queries = [
                    "//button[contains(@aria-label, 'One-click apply')]",
                    "//button[contains(text(), 'Quick Apply')]",
                    "//button[contains(text(), 'Instant Apply')]",
                    "//span[contains(text(), 'Apply Instantly')]"
                ]
                
                # Check for Quick Wins first
                for xp in quick_hunt_queries:
                    try:
                        btn = self.driver.find_element(By.XPATH, xp)
                        if btn.is_displayed():
                            yield "⚡ QUICK WIN detected! Sending application instantly..."
                            logger.info(f"Pilot: Quick Win detected via {xp}")
                            btn.click()
                            random_sleep(3, 5)
                            # Log and return
                            logger.info("Pilot: Application sent via Quick Win. Mission Success.")
                            yield "SUCCESS"
                            return
                    except: continue

                xp_queries = [
                    "//button[contains(@aria-label, 'Easy Apply')]",
                    "//button[contains(text(), 'Easy Apply')]",
                    "//span[text()='Easy Apply']",
                    "//div[contains(@class, 'jobs-apply-button')]",
                    "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'apply')]",
                    "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'apply')]"
                ]
                
                apply_element = None
                for xp in xp_queries:
                    try:
                        elements = self.driver.find_elements(By.XPATH, xp)
                        for el in elements:
                            if el.is_displayed():
                                apply_element = el
                                logger.info(f"Pilot: Found apply button candidate via {xp}")
                                break
                        if apply_element: break
                    except: continue

                if apply_element:
                    yield f"Found Apply Button ({apply_element.tag_name}). Clicking..."
                    logger.info("Pilot: Clicking apply button...")
                    self.driver.execute_script("arguments[0].style.border='3px solid red';", apply_element)
                    random_sleep(1, 2)
                    try: apply_element.click()
                    except: self.driver.execute_script("arguments[0].click();", apply_element)
                    random_sleep(4, 6)
                    
                    # --- COVER LETTER DECISION ---
                    # ...
                    
                    # --- UNIVERSAL FORM FILLING HANDOFF ---
                    yield "Engaging Autonomous Pilot for Form Completion..."
                    logger.info("Pilot: Handing off to LLMFormFiller...")
                    from backend.agents.llm_form_filler import LLMFormFiller
                    filler = LLMFormFiller(self.driver)
                    
                    if filler.fill_form(candidate_profile, smart_answers=smart_answers):
                        yield "AI Agent successfully processed form actions."
                        logger.info("Pilot: Form filler reports success.")
                        
                        # Check for Success Indicators (URL change, Success Message)
                        random_sleep(3, 5)
                        import time
                        ss_path = f"data/screenshots/app_{job_id}_{int(time.time())}.png"
                        os.makedirs("data/screenshots", exist_ok=True)
                        self.driver.save_screenshot(ss_path)
                        
                        # Check if we are back on search page or see 'applied' message
                        page_text = self.driver.page_source.lower()
                        if any(x in page_text for x in ["success", "applied", "submitted", "application sent"]):
                            # LOG TO DB
                            from backend.database import Application
                            new_app = Application(
                                job_id=job.id,
                                resume_id=resume.id,
                                status="Applied",
                                applied_at=datetime.utcnow(),
                                screenshot_path=ss_path
                            )
                            db.add(new_app)
                            db.commit()
                            yield "Mission Success! Application recorded. 🚀"
                            logger.info(f"Pilot: Mission Successful for {job.title}. Application recorded in DB.")
                            yield "SUCCESS"
                            return
                        else:
                            yield "Application initiated, but final confirmation not found on page."
                            logger.warning(f"Pilot: No final confirmation found for {job.title}. Marking as Failure for transparency.")
                            yield "FAILURE"
                            return
                    else:
                        yield "AI Agent stalled or found no actionable forms."
                        logger.warning(f"Pilot: Form filler failed or found no forms for {job.title}")
                        yield "FAILURE"
                        return

                else:
                   yield "No Apply or Easy-Apply buttons found on this page."
                   logger.warning(f"Pilot: Could not find any apply buttons for {job.title} at {job_data['url']}")
                   yield "FAILURE"
                   return
                    
            except Exception as e:
                logger.error(f"Application interaction failed: {e}")
                yield f"Error: {e}"
                yield "FAILURE"
                return
        except Exception as e:
             logger.error(f"DB Error: {e}")
             yield "FAILURE"
             return
        finally:
            db.close()

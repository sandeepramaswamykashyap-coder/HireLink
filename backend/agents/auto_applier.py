from backend.utils.selenium_utils import setup_driver, random_sleep
from backend.database import get_db, Job, Resume, Application
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
        
    def start_browser(self):
        if not self.driver:
            logger.info("Starting AutoApplier browser session...")
            self.driver = setup_driver(headless=False, detach=True)
            
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

    def apply_to_job(self, job_id, resume_id):
        # ... (Start of method same as before) ...
        # Ensure browser is running
        self.start_browser()
        
        from backend.database import SessionLocal
        db = SessionLocal()
        try:
            # 1. Fetch Data
            job = db.query(Job).filter_by(id=job_id).first()
            resume = db.query(Resume).filter_by(id=resume_id).first()
            
            if not job or not resume:
                logger.error("Job or Resume not found in DB")
                return False
                
            # 2. Extract Data to Pure Python
            job_data = {'id': job.id, 'title': job.title, 'company': job.company, 'url': job.url}
            resume_data = {'id': resume.id, 'name': resume.name, 'email': resume.email, 'phone': resume.phone}
            
            logger.info(f"Starting application for {job_data['title']} at {job_data['company']}")
            
            # 3. Navigation
            try:
                self.driver.get(job_data['url'])
                random_sleep(3, 5)
                
                # Enhanced Logic: Click "Easy Apply"
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
                                break
                        if apply_element: break
                    except: continue

                if apply_element:
                    logger.info(f"Found apply element: {apply_element.tag_name}, clicking...")
                    self.driver.execute_script("arguments[0].style.border='3px solid red';", apply_element)
                    random_sleep(1, 2)
                    try: apply_element.click()
                    except: self.driver.execute_script("arguments[0].click();", apply_element)
                    random_sleep(4, 6)
                    
                    # --- HANDLING LINKEDIN EASY APPLY MODAL ---
                    try:
                        modal = self.driver.find_element(By.CLASS_NAME, "jobs-easy-apply-modal")
                        logger.info("LinkedIn Easy Apply Modal detected!")
                        
                        max_steps = 10 # More steps allowed
                        for step in range(max_steps):
                            random_sleep(1, 2)
                            
                            # 1. INPUTS
                            try:
                                inputs = modal.find_elements(By.TAG_NAME, "input")
                                for inp in inputs:
                                    if not inp.is_displayed(): continue
                                    input_type = inp.get_attribute("type")
                                    lbl = (inp.get_attribute("name") or "") + " " + (inp.get_attribute("aria-label") or "") + " " + (inp.get_attribute("id") or "")
                                    val = inp.get_attribute("value")
                                    
                                    # Look for Question Label Check
                                    try:
                                        # Try to find a label element pointing to this input
                                        lbl_elem = self.driver.find_element(By.CSS_SELECTOR, f"label[for='{inp.get_attribute('id')}']")
                                        lbl += " " + lbl_elem.text
                                    except: pass

                                    # DB SMART LOOKUP
                                    smart_val = self.find_smart_answer(lbl)

                                    if input_type == "text" or input_type == "number":
                                        if val and len(val) > 0: continue # Skip filled
                                        
                                        if smart_val:
                                            inp.send_keys(smart_val)
                                        elif "first" in lbl.lower() and resume_data['name']:
                                            inp.send_keys(resume_data['name'].split()[0])
                                        elif "last" in lbl.lower() and resume_data['name']:
                                            inp.send_keys(resume_data['name'].split()[-1])
                                        elif "city" in lbl.lower():
                                            inp.send_keys("Bangalore")
                                        elif input_type == "number":
                                            inp.send_keys("5") # Fallback
                                        else:
                                            inp.send_keys("-") # Fallback

                                    elif input_type == "radio":
                                        # Check if this radio matches our smart Answer (Yes/No)
                                        # Radio logic is hard because 'value' might be 'true'/'false'
                                        # We rely on fieldset processing below for Radios usually
                                        pass
                                        
                                    elif input_type == "checkbox":
                                        try: self.driver.execute_script("arguments[0].click();", inp) 
                                        except: pass
                            except: pass

                            # 2. DROPDOWNS
                            try:
                                selects = modal.find_elements(By.TAG_NAME, "select")
                                for sel in selects:
                                    if not sel.is_displayed(): continue
                                    
                                    # Get Label/Context
                                    lbl = sel.get_attribute("name") or ""
                                    try:
                                        p = sel.find_element(By.XPATH, "./..")
                                        lbl += " " + p.text
                                    except: pass
                                    
                                    smart_val = self.find_smart_answer(lbl)
                                    
                                    try:
                                        from selenium.webdriver.support.ui import Select
                                        s = Select(sel)
                                        
                                        if smart_val:
                                            # Try finding option with this text
                                            try:
                                                s.select_by_visible_text(smart_val)
                                                continue
                                            except: pass # Text didn't match exactly
                                        
                                        # Fallback Logic
                                        options = [o.text.lower() for o in s.options]
                                        desired_indices = [i for i, txt in enumerate(options) if "yes" in txt or "professional" in txt or "native" in txt or "expert" in txt]
                                        if desired_indices: s.select_by_index(desired_indices[0])
                                        elif len(s.options) > 1: s.select_by_index(1)
                                    except: pass
                            except: pass

                            # 3. FIELDSETS (Radios)
                            try:
                                fieldsets = modal.find_elements(By.TAG_NAME, "fieldset")
                                for fs in fieldsets:
                                    lbl = fs.text.lower().split('\n')[0] # First line is usually question
                                    smart_val = self.find_smart_answer(lbl)
                                    
                                    if smart_val:
                                        self._click_radio(fs, smart_val)
                                    else:
                                        # Heuristic Fallback
                                        if "sponsorship" in lbl: self._click_radio(fs, "No")
                                        else: self._click_radio(fs, "Yes")
                            except: pass

                            # 2. Look for Buttons (Submit/Review/Next)
                            button_stage = None
                            submit_btns = modal.find_elements(By.XPATH, ".//button[contains(@aria-label, 'Submit application') or contains(text(), 'Submit application')]")
                            if submit_btns and submit_btns[0].is_displayed():
                                self.driver.execute_script("arguments[0].style.border='3px solid green';", submit_btns[0])
                                submit_btns[0].click()
                                logger.info("Clicked Submit!")
                                random_sleep(3, 5)
                                break 

                            review_btns = modal.find_elements(By.XPATH, ".//button[contains(@aria-label, 'Review your application') or contains(text(), 'Review')]")
                            if review_btns and review_btns[0].is_displayed():
                                review_btns[0].click()
                                continue

                            next_btns = modal.find_elements(By.XPATH, ".//button[contains(@aria-label, 'Continue to next step') or contains(text(), 'Next')]")
                            if next_btns and next_btns[0].is_displayed():
                                next_btns[0].click()
                                continue
                                
                            logger.warning("No navigation buttons found in modal.")
                            break
                            
                    except Exception as e:
                        logger.info(f"Not a LinkedIn modal or error: {e}")
                        
                        # Fallback to simple form filling (original logic)
                        try:
                            name_inputs = self.driver.find_elements(By.XPATH, "//input[contains(@name, 'name') or contains(@id, 'name') or contains(@autocomplete, 'name')]")
                            if name_inputs and resume_data['name']:
                                name_inputs[0].clear()
                                name_inputs[0].send_keys(resume_data['name'])
                        except: pass
                        
                        try:
                            email_inputs = self.driver.find_elements(By.XPATH, "//input[contains(@name, 'email') or contains(@type, 'email')]")
                            if email_inputs and resume_data['email']:
                                email_inputs[0].clear()
                                email_inputs[0].send_keys(resume_data['email'])
                        except: pass
                        
                        try:
                            phone_inputs = self.driver.find_elements(By.XPATH, "//input[contains(@name, 'phone') or contains(@type, 'tel')]")
                            if phone_inputs and resume_data['phone']:
                                phone_inputs[0].clear()
                                phone_inputs[0].send_keys(resume_data['phone'])
                        except: pass
                    
                    # Screenshot
                    if not os.path.exists("data/screenshots"):
                        os.makedirs("data/screenshots")
                        
                    screenshot_path = f"data/screenshots/app_{job_data['id']}_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
                    self.driver.save_screenshot(os.path.join(os.getcwd(), screenshot_path))
                    
                    # Log success
                    app = Application(
                        job_id=job_data['id'],
                        resume_id=resume_data['id'],
                        status="Form Filled (Action Required)", # Honest status
                        match_score=0.0,
                        screenshot_path=screenshot_path
                    )
                    db.add(app)
                    db.commit()
                    return True
                else:
                    logger.warning("No apply button found immediately.")
                    return False
                    
            except Exception as e:
                logger.error(f"Application interaction failed: {e}")
                return False
        except Exception as e:
             logger.error(f"DB Error or other: {e}")
             return False
        finally:
            db.close()

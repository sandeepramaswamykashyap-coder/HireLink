from backend.utils.selenium_utils import setup_driver, random_sleep
from backend.database import get_db, Job, Resume, Application
from backend.utils.logger import logger
from backend.agents.cover_letter_generator import CoverLetterGenerator
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from datetime import datetime

class AutoApplier:
    def __init__(self):
        self.cl_gen = CoverLetterGenerator()
        
    def apply_to_job(self, job_id, resume_id):
        from backend.database import SessionLocal
        db = SessionLocal()
        try:
            job = db.query(Job).filter_by(id=job_id).first()
            resume = db.query(Resume).filter_by(id=resume_id).first()
            
            if not job or not resume:
                logger.error("Job or Resume not found")
                return False
                
            logger.info(f"Starting application for {job.title} at {job.company}")
            
            driver = setup_driver(headless=False) # Headful to see action
            try:
                driver.get(job.url)
                random_sleep(3, 5)
                
                # Enhanced Heuristic: Look for "Apply" buttons or links
                xp_queries = [
                    "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'apply')]",
                    "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'apply')]",
                    "//input[@type='submit' and contains(translate(@value, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'apply')]",
                    "//button[contains(@class, 'apply')]",
                    "//a[contains(@class, 'apply')]"
                ]
                
                apply_element = None
                for xp in xp_queries:
                    try:
                        elements = driver.find_elements(By.XPATH, xp)
                        for el in elements:
                            if el.is_displayed():
                                apply_element = el
                                break
                        if apply_element:
                            break
                    except: continue

                if apply_element:
                    logger.info(f"Found apply element: {apply_element.tag_name}, clicking...")
                    try:
                        apply_element.click()
                    except:
                        driver.execute_script("arguments[0].click();", apply_element)
                    
                    random_sleep(2, 4)
                    
                    # Fill common fields if a form appears
                    # Name
                    try:
                        name_inputs = driver.find_elements(By.XPATH, "//input[contains(@name, 'name') or contains(@id, 'name')]")
                        if name_inputs and resume.name:
                            name_inputs[0].send_keys(resume.name)
                    except: pass
                    
                    # Email
                    try:
                        email_inputs = driver.find_elements(By.XPATH, "//input[contains(@name, 'email') or contains(@type, 'email')]")
                        if email_inputs and resume.email:
                            email_inputs[0].send_keys(resume.email)
                    except: pass
                    
                    # Phone
                    try:
                        phone_inputs = driver.find_elements(By.XPATH, "//input[contains(@name, 'phone') or contains(@type, 'tel')]")
                        if phone_inputs and resume.phone:
                            phone_inputs[0].send_keys(resume.phone)
                    except: pass
                    
                    # Screenshot
                    screenshot_path = f"data/screenshots/app_{job.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
                    driver.save_screenshot(f"IndianSmartApplier/{screenshot_path}")
                    
                    # Log success (Mocked success for now as actual submission is risky to automate blindly)
                    app = Application(
                        job_id=job.id,
                        resume_id=resume.id,
                        status="Applied (Simulated)",
                        match_score=0.0, # Should be passed in
                        screenshot_path=screenshot_path
                    )
                    db.add(app)
                    db.commit()
                    return True
                else:
                    logger.warning("No apply button found immediately.")
                    # Take debug screenshot
                    driver.save_screenshot(f"IndianSmartApplier/data/screenshots/failed_find_btn_{job.id}.png")
                    return False
                    
            except Exception as e:
                logger.error(f"Application failed: {e}")
                return False
            finally:
                driver.quit()
        finally:
            db.close()

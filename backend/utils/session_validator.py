from backend.utils.selenium_utils import setup_driver
from backend.utils.logger import logger
import time

class SessionValidator:
    def __init__(self):
        self.driver = None

    def start_driver(self):
        if not self.driver:
            # Setting headless=False so user can see the initial validation
            self.driver = setup_driver(headless=False)

    def close_driver(self):
        if self.driver:
            self.driver.quit()
            self.driver = None

    def check_linkedin(self):
        try:
            self.start_driver()
            logger.info("Verifying LinkedIn session...")
            self.driver.get("https://www.linkedin.com/feed/")
            time.sleep(3) # Wait for redirects
            
            # If we are on feed, we are good. If redirected to login/home, bad.
            current_url = self.driver.current_url
            if "linkedin.com/feed" in current_url:
                return True
            return False
        except Exception as e:
            logger.error(f"LinkedIn verification failed: {e}")
            return False

    def check_naukri(self):
        try:
            self.start_driver()
            logger.info("Verifying Naukri session...")
            self.driver.get("https://www.naukri.com/mnj/user/profile")
            time.sleep(3)
            
            current_url = self.driver.current_url
            if "nlogin" in current_url or "login" in current_url:
                return False
            return True
        except Exception as e:
            logger.error(f"Naukri verification failed: {e}")
            return False
            
    def check_indeed(self):
        try:
            self.start_driver()
            logger.info("Verifying Indeed session...")
            # Indeed is tricky, try checking settings
            self.driver.get("https://secure.indeed.com/account") 
            time.sleep(3)
            
            current_url = self.driver.current_url
            if "secure.indeed.com/auth" in current_url: # Redirected to auth
                return False
            return True
        except Exception as e:
             logger.error(f"Indeed verification failed: {e}")
             return False

    def check_all(self):
        results = {}
        try:
            results["LinkedIn"] = self.check_linkedin()
            results["Naukri"] = self.check_naukri()
            results["Indeed"] = self.check_indeed()
        finally:
            self.close_driver()
        return results

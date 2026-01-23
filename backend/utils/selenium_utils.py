from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from backend.utils.logger import logger
import time
import random
import os

try:
    from fake_useragent import UserAgent
except ImportError:
    UserAgent = None

def get_random_user_agent():
    try:
        if UserAgent:
            ua = UserAgent()
            return ua.random
    except:
        pass
    return "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def setup_driver(headless=True, profile_dir=None, detach=False):
    """Setup Chrome Driver with anti-detection options and optional profile persistence"""
    # --- SIMPLIFIED STABLE CONFIGURATION ---
    # Matches debug_chrome.py which was successful
    options = Options()
    
    # 1. Base Options
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    
    # 2. Window Size (Critical for UI consistency)
    options.add_argument('--window-size=1920,1080')
    
    if headless:
        options.add_argument('--headless=new')

    # 3. User Agent (Fixed)
    ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    options.add_argument(f'user-agent={ua}')

    # 4. Profile Management
    if not profile_dir:
        profile_dir = os.path.join(os.getcwd(), "data", "chrome_profile")
    
    # Ensure dir exists
    if not os.path.exists(profile_dir):
        os.makedirs(profile_dir, exist_ok=True)
        
    options.add_argument(f"user-data-dir={profile_dir}")
    logger.info(f"Using Chrome Profile: {profile_dir}")

    # 5. Initialization with Retry
    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting to start Chrome Driver (Attempt {attempt + 1}/{max_retries})...")
            service = Service(ChromeDriverManager().install())
            
            # Fallback for last attempt
            if attempt == max_retries - 1:
                logger.warning("⚠️ Using FINAL FALLBACK options (No Profile)")
                fb_opts = Options()
                fb_opts.add_argument('--no-sandbox')
                fb_opts.add_argument('--disable-dev-shm-usage')
                fb_opts.add_argument('--headless=new')
                fb_opts.add_argument(f"user-agent={ua}")
                driver = webdriver.Chrome(service=service, options=fb_opts)
            else:
                driver = webdriver.Chrome(service=service, options=options)

            # Minimal Anti-Detection (Safe)
            try:
                driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            except: pass
            
            logger.info("Chrome Driver initialized successfully.")
            return driver
        except Exception as e:
            logger.warning(f"Driver Init Failed (Attempt {attempt + 1}): {e}")
            time.sleep(2)
            if attempt == max_retries - 1:
                logger.error(f"CRITICAL: Engine Failed. {e}")
                raise RuntimeError(f"Browser Engine Blocked: {e}")


def save_cookies(driver, path):
    """Save cookies to a file"""
    import pickle
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as file:
            pickle.dump(driver.get_cookies(), file)
        logger.info(f"Cookies saved to {path}")
        return True
    except Exception as e:
        logger.warning(f"Failed to save cookies: {e}")
        return False

def load_cookies(driver, path, domain=None):
    """Load cookies from a file"""
    import pickle
    try:
        if not os.path.exists(path):
            return False
            
        with open(path, 'rb') as file:
            cookies = pickle.load(file)
            
        # Add cookies to driver
        driver.execute_cdp_cmd('Network.enable', {})
        for cookie in cookies:
            try:
                # Fix for domain mismatch issues
                if domain and domain not in cookie.get('domain', ''):
                    continue
                    
                # Clean up cookie fields that might cause errors
                if 'expiry' in cookie:
                    cookie['expires'] = cookie['expiry']
                    del cookie['expiry']
                
                driver.add_cookie(cookie)
            except Exception as e:
                # Some cookies fail to add, just ignore
                pass
                
        logger.info(f"Cookies loaded from {path}")
        return True
    except Exception as e:
        logger.warning(f"Failed to load cookies: {e}")
        return False

def random_sleep(min_seconds=2, max_seconds=5):
    """Sleep for a random amount of time to mimic human behavior"""
    time.sleep(random.uniform(min_seconds, max_seconds))


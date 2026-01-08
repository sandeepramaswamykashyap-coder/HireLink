from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent
from backend.utils.logger import logger
import time
import random
import os

def get_random_user_agent():
    try:
        ua = UserAgent()
        return ua.random
    except:
        return "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def setup_driver(headless=True, profile_dir=None, detach=False):
    """Setup Chrome Driver with anti-detection options and optional profile persistence"""
    options = Options()
    
    if headless:
        options.add_argument('--headless=new')
    
    if detach:
        options.add_experimental_option("detach", True)
        
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    # options.add_argument('--remote-debugging-port=9222') # REMOVED: Causes conflicts if multiple instances run
    options.add_argument('--disable-search-engine-choice-screen')
    
    # Use a FIXED User-Agent to ensure session cookies remain valid
    # Randomizing it causes sites to think it's a new device, invalidating the login.
    fixed_ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    options.add_argument(f'user-agent={fixed_ua}')
    
    # Profile Persistence
    if profile_dir:
        options.add_argument(f"user-data-dir={profile_dir}")
        logger.info(f"Using custom profile: {profile_dir}")
    else:
        # If no profile specified, let Selenium create a fresh temp profile automatically.
        # This is the safest way to avoid locking conflicts.
        logger.info("Using native temporary profile (isolated session)")
    
    # Anti-detection
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # Additional anti-detection scripts
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        logger.info("Chrome Driver setup successfully.")
        return driver
    except Exception as e:
        logger.error(f"Failed to setup Chrome Driver: {e}")
        raise

def random_sleep(min_seconds=2, max_seconds=5):
    """Sleep for a random amount of time to mimic human behavior"""
    time.sleep(random.uniform(min_seconds, max_seconds))

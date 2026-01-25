import time
import os
import shutil
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

def test_browser():
    print("--- CHROME DEBUG DIAGNOSTIC ---")
    
    # 1. CLEANUP
    profile_dir = os.path.join(os.getcwd(), "data", "debug_profile")
    if os.path.exists(profile_dir):
        shutil.rmtree(profile_dir)
    os.makedirs(profile_dir, exist_ok=True)
    print(f"1. Created fresh profile at: {profile_dir}")
    
    # 2. MANAGER
    try:
        print("2. Installing/Finding ChromeDriver...")
        driver_path = ChromeDriverManager().install()
        print(f"   Success! Path: {driver_path}")
    except Exception as e:
        print(f"   FAILED to install driver: {e}")
        return

    # 3. OPTIONS
    print("3. Configuring Options...")
    options = Options()
    # options.add_argument('--headless=new') # Try headless first
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument(f"user-data-dir={profile_dir}")
    
    # 4. LAUNCH
    print("4. Attempting Launch...")
    try:
        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=options)
        print("   ✅ SUCCESS! Chrome launched.")
        
        driver.get("https://www.google.com")
        print("   Navigated to Google: " + driver.title)
        
        driver.quit()
        print("   Closed successfully.")
    except Exception as e:
        print(f"   ❌ CRITICAL FAILURE: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_browser()

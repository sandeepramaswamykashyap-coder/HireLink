from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import sys

def run_smoke_test():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=options)
    driver.get("http://localhost:8502")
    
    try:
        print("1. Opening Homepage...")
        WebDriverWait(driver, 10).until(EC.title_contains("Hire Link"))
        print("   ✅ Homepage Loaded")
        
        # Streamlit creates IFrame or Shadow DOMs sometimes, 
        # but usually main content is accessible.
        # Wait for main container
        time.sleep(3) 
        
        # Check for Navigation
        # Streamlit sidebar navigation
        print("2. Verifying Sidebar...")
        # Accessing sidebar might be tricky due to Streamlit structure.
        # Let's check for specific text on the page
        src = driver.page_source
        if "Dashboard" in src and "Job Search" in src:
            print("   ✅ Sidebar Navigation visible")
        else:
            raise Exception("Sidebar not found")
            
        print("3. Checking Dashboard Stats...")
        # Look for "Opportunities Found"
        if "Opportunities Found" in driver.page_source:
             print("   ✅ Dashboard Stats visible")
        else:
             raise Exception("Dashboard stats missing")
             
        print("Smoke Test Passed!")
        
    except Exception as e:
        print(f"❌ Test Failed: {e}")
        sys.exit(1)
    finally:
        driver.quit()

if __name__ == "__main__":
    run_smoke_test()

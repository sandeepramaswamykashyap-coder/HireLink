
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.utils.selenium_utils import setup_driver
from selenium.webdriver.chrome.options import Options

def test_proxy_injection():
    print("--- TESTING PROXY INJECTION ---")
    
    # 1. Set Env Var
    test_proxy = "127.0.0.1:9000"
    os.environ['PROXY_SERVER'] = test_proxy
    
    # 2. Mocking Options/Service to avoid actual browser launch if possible, 
    # but selenium_utils instantiates real objects. 
    # We will just start it and check capabilities if possible, or just check logs (if we could capture them).
    # Easier: Inspect the source code or trust the logic? 
    # Better: Use the driver to check capabilities.
    
    try:
        # Launch Driver (Headless)
        driver = setup_driver(headless=True)
        
        # Check Capabilities
        # Chrome stores proxy config in 'chrome.options' or distinct capability
        caps = driver.capabilities
        print(f"Driver Capabilities Keys: {list(caps.keys())}")
        
        # Depending on driver version, it might be in 'goog:chromeOptions' -> args
        chrome_opts = caps.get('goog:chromeOptions', {})
        args = chrome_opts.get('args', [])
        
        proxy_arg_found = any(f"--proxy-server={test_proxy}" in arg for arg in args)
        
        if proxy_arg_found:
             print("✅ SUCCESS: Proxy argument found in Chrome Options.")
        else:
             # Fallback check - sometimes it's processed into a proxy dict
             proxy_obj = caps.get('proxy', {})
             print(f"Proxy Object: {proxy_obj}")
             
             # Note: --proxy-server arg is often reflected in args list, but sometimes not if processed by driver manager.
             # However, we added it via options.add_argument, so it SHOULD be in args.
             print(f"Actual Args: {args}")
             
             if any('proxy-server' in arg for arg in args):
                 print("✅ SUCCESS: Proxy argument detected in args list.")
             else:
                 print("❌ FAILURE: Proxy argument NOT found.")

        driver.quit()
        
    except Exception as e:
        print(f"Test Failed: {e}")

if __name__ == "__main__":
    test_proxy_injection()

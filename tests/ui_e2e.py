
import pytest
from playwright.sync_api import Page, expect

def test_app_title(page: Page):
    # Using 8501 (Force)
    page.goto("http://localhost:8501")
    
    # Wait for Streamlit to load
    page.wait_for_selector("div[class*='stApp']", state="attached", timeout=15000)
    
    # Check Title
    expect(page).to_have_title("HireLink v2.5 (Core Upgrade)")

def test_sidebar_presence(page: Page):
    page.goto("http://localhost:8501")
    page.wait_for_selector("div[class*='stApp']", state="attached")
    
    # Try generic testid
    sidebar = page.locator("[data-testid='stSidebar']")
    expect(sidebar).to_be_visible()
    
def test_mission_control_elements(page: Page):
    page.goto("http://localhost:8501")
    page.wait_for_selector("div[class*='stApp']", state="attached")
    
    # "Mission Control" is likely in an H3 or specific class. 
    # Let's try to match content broadly
    expect(page.locator("body")).to_contain_text("Mission Control")


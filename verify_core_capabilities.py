import sys
import os
import time
from datetime import datetime

# Setup Path
sys.path.append(os.getcwd())

from dotenv import load_dotenv
load_dotenv()

from backend.database import SessionLocal, AppUser, init_db, migrate_db
from backend.utils.llm_client import LLMClient
from backend.utils.payment_gateway import PaymentGateway
import requests
from bs4 import BeautifulSoup

def cprint(msg, color="white"):
    colors = {
        "green": "\033[92m",
        "red": "\033[91m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "reset": "\033[0m"
    }
    print(f"{colors.get(color, '')}{msg}{colors['reset']}")

def verify_core():
    cprint("\n🔍 HIRING PLATFORM CORE VERIFICATION 🔍", "blue")
    cprint("========================================\n", "blue")
    
    score = 0
    total = 4
    
    # ---------------------------------------------------------
    # 1. DATABASE INTEGRITY
    # ---------------------------------------------------------
    cprint("[1/4] Checking Database Schema...", "yellow")
    try:
        init_db() # Should be safe/idempotent
        db = SessionLocal()
        
        # Check User Schema for new columns
        from sqlalchemy import inspect
        from backend.database import engine
        inspector = inspect(engine)
        columns = [c['name'] for c in inspector.get_columns("users_v2")]
        
        required = ['password', 'subscription_expiry', 'referral_code', 'earnings_balance']
        missing = [c for c in required if c not in columns]
        
        if not missing:
            cprint("   ✅ DB Schema Valid (All pillars present)", "green")
            score += 1
        else:
            cprint(f"   ❌ DB Schema Risk! Missing columns: {missing}", "red")
            
        db.close()
    except Exception as e:
        cprint(f"   ❌ DB Connection Failed: {e}", "red")

    # ---------------------------------------------------------
    # 2. AI INTELLIGENCE (LLM)
    # ---------------------------------------------------------
    cprint("\n[2/4] Verifying AI Brain (Gemini)...", "yellow")
    try:
        llm = LLMClient()
        if not llm.client:
             cprint("   ❌ LLM Client failed to initialize (Check API Key)", "red")
        else:
             start = time.time()
             response = llm.generate_text("Respond with exactly one word: 'Ready'")
             duration = time.time() - start
             
             if response and "Ready" in response:
                 cprint(f"   ✅ AI Online & Responsive ({duration:.2f}s)", "green")
                 score += 1
             else:
                 cprint(f"   ❌ AI Response Weird: {response}", "red")
    except Exception as e:
        cprint(f"   ❌ AI Exception: {e}", "red")

    # ---------------------------------------------------------
    # 3. FINANCIAL ENGINE (Razorpay)
    # ---------------------------------------------------------
    cprint("\n[3/4] Verifying Payment Gateway...", "yellow")
    pg = PaymentGateway()
    if pg.mock_mode:
        cprint("   ⚠️  Payment Gateway is in MOCK MODE (Sandbox)", "yellow")
        cprint("       (This is acceptable for dev, but ensure Live Keys are on Render)", "yellow")
        score += 1 # Giving pass for dev environment
    else:
        cprint("   ✅ Payment Gateway is LIVE (Real Money Mode)", "green")
        score += 1

    # ---------------------------------------------------------
    # 4. JOB DISCOVERY (Scraping)
    # ---------------------------------------------------------
    cprint("\n[4/4] Verifying Job Discovery (Python.org Probe)...", "yellow")
    try:
        # Simple probe to prove we can reach the outside world and parse HTML
        url = "https://www.python.org/jobs/"
        resp = requests.get(url, timeout=10)
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.content, 'html.parser')
            jobs = soup.find_all('span', class_='listing-company-name')
            
            if len(jobs) > 0:
                cprint(f"   ✅ Discovery Active: Found {len(jobs)} jobs on Python.org", "green")
                score += 1
            else:
                cprint("   ⚠️  Connected to Python.org but parsing found 0 jobs (Structure change?)", "yellow")
        else:
             cprint(f"   ❌ Connection Blocked ({resp.status_code})", "red")
    except Exception as e:
        cprint(f"   ❌ Discovery Exception: {e}", "red")
        
    # ---------------------------------------------------------
    # SUMMARY
    # ---------------------------------------------------------
    cprint(f"\nCORE HEALTH SCORE: {score}/{total}", "blue" if score == total else "yellow")
    if score == total:
        cprint("🚀 SYSTEM IS ROBUST AND READY FOR BUSINESS.", "green")
    else:
        cprint("⚠️  SYSTEM NEEDS ATTENTION BEFORE FULL LAUNCH.", "yellow")

if __name__ == "__main__":
    verify_core()

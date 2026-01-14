import streamlit as st
st.set_page_config(page_title="Hire Link", layout="wide", initial_sidebar_state="expanded")

# --- RESUME SEEDING DATA (Sanitized) ---
SEED_RESUME_DATA = {
    "name": "SANDEEP KASHYAP",
    "email": "sandeepramaswamykashyap@gmail.com",
    "phone": "+91 6366325217",
    "skills": ["UAT Planning & Execution", "Process Automation", "AI Agent Workflow Design", "Google Anti Gravity", "Technical Analysis"],
    "experience": [{"role": "Manager - HR Digital Services", "company": "Standard Chartered", "years": "2019-Now"}],
    "raw_full": """{"name": "SANDEEP KASHYAP", "email": "sandeepramaswamykashyap@gmail.com", "phone": "+91 6366325217", "summary": "Extensive Experience: 13+ years...", "skills": ["UAT Planning & Execution", "Process Automation in Recruitment", "AI Agent Workflow Design", "Google Anti Gravity", "Vibe Coding"], "experience": [{"role": "Manager - HR Digital Services", "company": "Standard Chartered Global Business Service", "years": "February 2019 - Now"}, {"role": "Team Lead - Client On-Boarding", "company": "Wipro Ltd", "years": "January 2015 - February 2019"}]}"""
}

def auto_seed_resume():
    try:
        from backend.database import SessionLocal, Resume, AppUser
        import json
        db = SessionLocal()
        
        # Check if user exists
        user = db.query(AppUser).filter_by(email=SEED_RESUME_DATA['email']).first()
        if user:
             # Check if resume exists
             res = db.query(Resume).filter_by(email=SEED_RESUME_DATA['email']).first()
             if not res:
                 print(f"⚠️ Seeding Resume for {user.name}...")
                 new_res = Resume(
                     name=SEED_RESUME_DATA['name'],
                     email=SEED_RESUME_DATA['email'],
                     phone=SEED_RESUME_DATA['phone'],
                     parsed_data=json.loads(SEED_RESUME_DATA['raw_full']),
                     raw_text=SEED_RESUME_DATA['raw_full'],
                     file_path="manual_seed_v1"
                 )
                 db.add(new_res)
                 db.commit()
                 print("✅ Resume Seeded!")
             else:
                 # Force Update with new details
                 res.parsed_data = json.loads(SEED_RESUME_DATA['raw_full'])
                 res.raw_text = SEED_RESUME_DATA['raw_full']
                 db.commit()
                 print("✅ Resume Updated.")
        db.close()
    except Exception as e:
        print(f"Seed Error: {e}")

# Run Seed
# auto_seed_resume() # DISABLED TO PREVENT ZOMBIE RESUMES

# --- END SEED ---

# --- NLTK SETUP (Critical for Text Processing) ---
import nltk
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    try:
        nltk.download('punkt', quiet=True)
    except (FileExistsError, Exception):
        pass  # Already downloaded or concurrent download in progress
try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    try:
        nltk.download('punkt_tab', quiet=True)
    except (FileExistsError, Exception):
        pass  # Already downloaded or concurrent download in progress
# -------------------------------------------------
import pandas as pd
import threading
import time
from datetime import datetime
import backend.database # Import module directly
from sqlalchemy import func
import importlib
importlib.reload(backend.database) # FORCE RELOAD to see new Coupon table

# importlib.reload logic removed for stability
import sys
# FORCE RELOAD of LLM Client to pick up model fix
if 'backend.utils.llm_client' in sys.modules:
    # safe try/except just in case
    try: del sys.modules['backend.utils.llm_client']
    except: pass

# Removed aggressive auto_applier unload to prevent KeyError
# if 'backend.agents.auto_applier' in sys.modules:
#     del sys.modules['backend.agents.auto_applier']

from backend.agents.auto_applier import AutoApplier

from backend.database import init_db, get_db, Job, Resume, Application, PortalStatus, QuestionAnswer, Coupon, PortalCredential, SessionLocal
# FORCE DB INIT to create new tables
init_db()
from backend.scrapers.naukri import NaukriScraper
from backend.scrapers.linkedin import LinkedInScraper
from backend.scrapers.indeed import IndeedScraper
from backend.scrapers.others import (
    ShineScraper, GlassdoorScraper, FounditScraper, 
    IntershalaScraper, IIMJobsScraper, FreshersworldScraper, WellfoundScraper
)
from backend.utils.payment_gateway import PaymentGateway
pg = PaymentGateway()
from backend.agents.resume_parser import ResumeParserV2 as ResumeParser
from backend.agents.job_matcher import JobMatcher
from backend.agents.auto_applier import AutoApplier
from backend.agents.job_analyzer import JobAnalyzer
import os
import time



# --- CAPTURE REFERRAL ---
if "ref" in st.query_params:
    st.session_state['captured_ref'] = st.query_params["ref"]

# --- LEGAL PAGES ROUTING (Razorpay Compliance) ---
if "page" in st.query_params:
    page_id = st.query_params["page"]
    from backend.config import legal_content
    
    legal_map = {
        "privacy": legal_content.PRIVACY_POLICY,
        "terms": legal_content.TERMS_AND_CONDITIONS,
        "refund": legal_content.REFUND_POLICY,
        "shipping": legal_content.SHIPPING_POLICY,
        "contact": legal_content.CONTACT_US
    }
    
    if page_id in legal_map:
        st.markdown(f'<a href="/" target="_self" style="text-decoration:none;">← Back to Home</a>', unsafe_allow_html=True)
        st.markdown(legal_map[page_id])
        st.stop()  # Stop rendering the rest of the app

# Load Custom CSS
# Load Custom CSS
st.markdown("""<style>
/* MISSION CONTROL PHASES (FIXED) */
.mission-phases {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: rgba(15, 23, 42, 0.6);
    padding: 15px 20px;
    border-radius: 12px;
    margin-bottom: 20px;
    border: 1px solid rgba(255, 255, 255, 0.05);
}

.phase-item {
    display: flex;
    align-items: center;
    gap: 8px;
    opacity: 0.4;
    transition: all 0.3s ease;
}

.phase-item.active {
    opacity: 1;
    transform: scale(1.05);
}

.phase-item.completed {
    opacity: 0.8;
    color: #10b981;
}

.phase-dot {
    font-size: 1.2rem;
    filter: drop-shadow(0 0 5px rgba(255,255,255,0.2));
}

.phase-label {
    font-size: 0.9rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.phase-item.active .phase-label {
    color: #0ea5e9;
    text-shadow: 0 0 10px rgba(14, 165, 233, 0.5);
}

/* ADMIN CONSOLE - SCRAPER HEALTH */
.status-card {
    background: rgba(30, 41, 59, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    padding: 15px;
    text-align: center;
    margin-bottom: 15px;
    transition: all 0.3s ease;
}

.status-card.online {
    border-color: rgba(16, 185, 129, 0.3);
    background: rgba(16, 185, 129, 0.05);
}

.status-card.offline {
    border-color: rgba(239, 68, 68, 0.3);
    background: rgba(239, 68, 68, 0.05);
}

.status-icon {
    font-size: 1.5rem;
    margin-bottom: 8px;
}

.status-name {
    font-size: 0.9rem;
    font-weight: 700;
    color: white;
    margin-bottom: 5px;
}

.status-badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
}

.status-badge.online {
    background: rgba(16, 185, 129, 0.2);
    color: #34d399;
}

.status-badge.offline {
    background: rgba(239, 68, 68, 0.2);
    color: #f87171;
}

.job-count {
    margin-top: 8px;
    font-size: 0.8rem;
    color: #94a3b8;
}

/* GOOGLE FONTS */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Outfit:wght@400;700;900&display=swap');

/* --- VARS --- */
:root {
    --bg-deep: #020617;
    --bg-surface: #0f172a;
    --bg-card: rgba(30, 41, 59, 0.4);

    /* Professional Blue/Indigo Theme */
    --primary: #4f46e5;
    /* Indigo 600 */
    --primary-hover: #4338ca;
    /* Indigo 700 */
    --accent: #0ea5e9;
    /* Sky 500 */
    --success: #10b981;
    /* Emerald 500 */

    /* Button Gradient (Professional) */
    --gradient-btn: linear-gradient(135deg, #4f46e5 0%, #4338ca 100%);

    /* Subtle Gradient for Headers only */
    --gradient-hero: linear-gradient(135deg, #f8fafc 0%, #94a3b8 100%);
    --gradient-glass: linear-gradient(180deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.01) 100%);

    --glow: 0 0 15px rgba(79, 70, 229, 0.3);
    --border: rgba(255, 255, 255, 0.1);
}

/* --- ANIMATIONS --- */
@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(10px);
    }

    to {
        opacity: 1;
        transform: translateY(0);
    }
}

/* --- BASE SETUP --- */
html,
body,
.stApp {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    background-color: var(--bg-deep);
    color: #f8fafc;
    font-size: 18px !important;
    /* Increased from 16px */
}

/* GLOBAL TEXT BOOST */
p,
.stMarkdown,
.stText,
.stCaption,
li,
span,
div {
    font-size: 1.1rem;
    /* Increased from 1rem */
    line-height: 1.6;
}

/* --- TYPOGRAPHY --- */
h1,
h2,
h3 {
    font-family: 'Outfit', sans-serif !important;
    letter-spacing: -0.02em;
    color: white !important;
}

h1 {
    font-size: 2.5rem !important;
    margin-bottom: 1.5rem !important;
}

.gradient-text {
    background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: inherit !important;
    font-weight: inherit !important;
    line-height: inherit !important;
}

/* --- DASHBOARD COMPONENTS --- */
.job-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 20px;
    backdrop-filter: blur(12px);
    transition: all 0.3s ease;
}

.job-card:hover {
    transform: translateY(-5px);
    border-color: var(--primary);
}

.match-score-badge {
    background: rgba(16, 185, 129, 0.1);
    color: #34d399;
    padding: 6px 12px;
    border-radius: 12px;
    font-weight: 800;
}

/* --- LANDING PAGE (PREMIUM) --- */
.landing-wrapper {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

.landing-hero {
    padding: 40px 20px;
    /* Reduced from 80px */
    text-align: center;
    background: radial-gradient(circle at center, rgba(79, 70, 229, 0.1) 0%, transparent 70%);
}

.landing-title {
    font-size: 5rem !important;
    /* Specificity Fix + Increased Size */
    font-weight: 900 !important;
    line-height: 1.1 !important;
    margin-bottom: 25px !important;
    letter-spacing: -3px;
}

.landing-subtitle {
    font-size: 1.25rem !important;
    color: #94a3b8 !important;
    max-width: 700px;
    margin: 0 auto 50px !important;
}

.landing-features {
    display: flex;
    /* Changed from Grid to Flex */
    flex-wrap: wrap;
    justify-content: center;
    gap: 25px;
    margin: 40px 0;
    /* Reduced from 60px */
}

.feature-card {
    background: rgba(30, 41, 59, 0.5);
    border: 1px solid var(--border);
    border-radius: 24px;
    padding: 25px;
    /* Reduced from 40px */
    text-align: left;
    transition: all 0.3s ease;
    flex: 1 1 300px;
    /* Flexbox sizing */
    max-width: 400px;
}

.feature-card:hover {
    transform: translateY(-8px);
    border-color: var(--primary);
    background: rgba(30, 41, 59, 0.8);
}

.feature-icon {
    font-size: 2.5rem;
    margin-bottom: 20px;
    display: block;
}

.portal-grid {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 15px;
    margin-top: 40px;
}

.portal-item {
    background: rgba(255, 255, 255, 0.05);
    padding: 15px;
    border-radius: 12px;
    text-align: center;
    border: 1px solid var(--border);
    transition: 0.3s;
}

.portal-item:hover {
    background: var(--primary);
    color: white;
    transform: translateY(-3px);
}

/* --- MISSION CONTROL --- */
.mission-header {
    background: linear-gradient(90deg, #1e1b4b 0%, #312e81 100%);
    border: 1px solid rgba(99, 102, 241, 0.4);
    border-radius: 12px;
    padding: 15px 25px;
    margin-bottom: 20px;
    display: flex;
}

.m-stat {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 15px;
    text-align: center;
}

/* --- WIDGET GLOW UP (GLASSMORPHISM) --- */
/* Inputs */
.stTextInput input, .stSelectbox, .stMultiSelect, .stTextArea textarea {
    background-color: rgba(255, 255, 255, 0.03) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    color: white !important;
    border-radius: 12px !important;
    transition: all 0.2s ease;
}

.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: var(--primary) !important;
    box-shadow: 0 0 15px rgba(79, 70, 229, 0.3) !important;
    background-color: rgba(255, 255, 255, 0.07) !important;
}

/* Dataframes / Tables */
div[data-testid="stDataFrame"] {
    background: transparent !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 12px;
    padding: 10px;
}

div[data-testid="stTable"] {
    background: transparent !important;
}

/* Metrics */
div[data-testid="stMetricValue"] {
    font-size: 2rem !important;
    font-weight: 800 !important;
    background: linear-gradient(90deg, #fff 0%, #cbd5e1 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

div[data-testid="stMetricLabel"] {
    color: #94a3b8 !important;
    font-size: 0.9rem !important;
    text-transform: uppercase;
    letter-spacing: 1px;
/* Tabs - FULL WIDTH SEGMENTED CONTROL */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px !important;
    background: rgba(255,255,255,0.03) !important;
    padding: 8px !important;
    border-radius: 12px !important;
    border: 1px solid rgba(255,255,255,0.05) !important;
    display: flex !important;
}

.stTabs [data-baseweb="tab"] {
    height: 50px !important;
    white-space: pre-wrap !important;
    background-color: transparent !important;
    border-radius: 8px !important;
    color: #94a3b8 !important;
    font-weight: 600 !important;
    transition: all 0.2s !important;
    font-size: 1rem !important;
    border: none !important;
    flex-grow: 1 !important; /* Expand to fill space */
    text-align: center !important;
    justify-content: center !important;
}

.stTabs [data-baseweb="tab"]:hover {
    background-color: rgba(255,255,255,0.05) !important;
    color: white !important;
}

.stTabs [aria-selected="true"] {
    background-color: #4f46e5 !important; /* Indigo Primary */
    color: white !important;
    box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3) !important;
}

/* Hide Default Streamlit Tab Decorations */
.stTabs [data-baseweb="tab-highlight"], 
.stTabs [data-baseweb="tab-border"] {
    display: none !important;
    height: 0 !important;
    width: 0 !important;
}

/* Sidebar Override */
[data-testid="stSidebar"] {
    background-color: #020617 !important;
    border-right: 1px solid rgba(255,255,255,0.05);
}

/* Global Glass Card Class for Internal Use */
.glass-card {
    background: rgba(30, 41, 59, 0.4);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 20px;
}

/* Button Refinement */
.stButton button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    padding: 0.5rem 1rem !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    background: rgba(255,255,255,0.05);
    color: white;
    transition: all 0.2s;
}

.stButton button:hover {
    border-color: var(--primary) !important;
    background: rgba(79, 70, 229, 0.1);
    transform: translateY(-2px);
}

button[kind="primary"] {
    background: var(--gradient-btn) !important;
    border: none !important;
    box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
}

/* --- PRICING SECTION --- */
.pricing-section {
    padding: 20px;
    /* Reduced from 60px 20px */
    max-width: 1200px;
    margin: 0 auto;
}

.pricing-grid {
    display: flex;
    justify-content: center;
    gap: 30px;
    flex-wrap: wrap;
    margin-top: 40px;
}

.pricing-card {
    background: #1e293b;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 20px;
    padding: 40px 30px;
    width: 100%;
    max-width: 380px;
    margin: 0 auto 20px auto;
    text-align: center;
    position: relative;
    transition: 0.3s;
    display: flex;
    flex-direction: column;
    min-height: 480px;
}

.pricing-card:hover {
    transform: translateY(-8px);
    box-shadow: 0 20px 40px -10px rgba(0, 0, 0, 0.5);
}

.pricing-header {
    margin-bottom: 30px;
}

.plan-name {
    font-size: 0.9rem;
    font-weight: 700;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 10px;
}

.price-tag {
    font-size: 3rem;
    font-weight: 800;
    color: white;
    line-height: 1;
    margin-bottom: 8px;
}

.pricing-features {
    text-align: left;
    margin-bottom: 40px;
    flex-grow: 1;
}

.pricing-features ul {
    list-style: none;
    padding: 0;
    margin: 0;
}

.pricing-features li {
    margin-bottom: 15px;
    display: flex;
    align-items: center;
    gap: 10px;
    color: #e2e8f0;
    font-size: 0.95rem;
}

.pricing-features li::before {
    content: "✓";
    color: #10b981;
    font-weight: 800;
}

/* MISSION CONTROL UI */
.mission-header {
    background: linear-gradient(90deg, #1e1b4b 0%, #312e81 100%);
    border: 1px solid rgba(99, 102, 241, 0.4);
    border-radius: 12px;
    padding: 15px 25px;
    margin-bottom: 20px;
}

.m-stat {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    padding: 20px 10px;
    text-align: center;
    transition: all 0.3s ease;
}

.m-stat:hover {
    transform: translateY(-5px);
    border-color: var(--primary);
}

.m-stat-val {
    font-size: 1.8rem;
    font-weight: 800;
    color: white;
}

.m-stat-label {
    font-size: 0.7rem;
    color: #94a3b8;
    text-transform: uppercase;
    font-weight: 600;
}
</style>""", unsafe_allow_html=True)



db = next(get_db())

def get_db_session():
    from backend.database import SessionLocal
    return SessionLocal()

def launch_login_browser():
    from backend.utils import selenium_utils
    # Reload removed
    from backend.utils.selenium_utils import setup_driver
    
    st.info("Launching browser... Please login to Naukri, LinkedIn, Indeed manually in the popped-up window.")
    st.warning("Do NOT close the terminal/app. Close the browser window when done.")
    
    try:
        driver = setup_driver(headless=False, detach=True)
        driver.get("https://www.naukri.com/nlogin/login")
        
        st.success("Browser launched! Please OPEN NEW TABS for LinkedIn and Indeed manually and login.")
        st.info("1. Login to Naukri in the open tab.\n2. Open a new tab -> go to linkedin.com -> login.\n3. Open a new tab -> go to indeed.com -> login.")
        time.sleep(2) 
    except Exception as e:
        error_msg = str(e).lower()
        if "devtoolsactiveport" in error_msg or "chrome failed to start" in error_msg:
             st.error("❌ Cloud Environment Detected: Cannot launch local browser.")
             st.info("Since you are running on Streamlit Cloud, the app cannot open a window on your computer. Please enter your credentials in the **'Keys'** tab inside the dashboard instead.")
        else:
             st.error(f"Failed to launch browser: {e}")


# --- FLOATING CHATBOT (Bubble) ---
def render_floating_chat():
    # CSS to float the popover button to bottom-right
    st.markdown("""
    <style>
    /* Float the Popover Container */
    [data-testid="stPopover"] {
        position: fixed;
        bottom: 30px;
        right: 30px;
        z-index: 9000;
    }
    
    /* Style the Button to match "Bubble" look */
    [data-testid="stPopover"] button {
        width: 60px;
        height: 60px;
        border-radius: 30px;
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        box-shadow: 0 4px 20px rgba(79, 70, 229, 0.5);
        border: none;
        color: white;
        font-size: 1.5rem;
        transition: transform 0.2s;
    }
    
    [data-testid="stPopover"] button:hover {
        transform: scale(1.1);
        box-shadow: 0 6px 25px rgba(79, 70, 229, 0.7);
    }
    
    /* Popover Content Window */
    /* Note: Streamlit popovers are absolute positioned by the library, 
       but we can try to style the content if needed. */
    </style>
    """, unsafe_allow_html=True)

    # Fallback for older Streamlit versions
    try:
        chat_container_widget = st.popover("💬", help="AI Assistant")
    except AttributeError:
        # Fallback: Use an expander in the sidebar or bottom
        # Since we are floating, an expander might look weird if not handled.
        # Let's just use a fixed expander at the bottom if possible, or revert to sidebar logic.
        # Easiest: Use st.expander in the main flow, but we are already floating.
        # Let's force a sidebar expander as fallback.
        chat_container_widget = st.sidebar.expander("💬 Chat (Fallback)", expanded=st.session_state.get("chat_open", False))

    with chat_container_widget:
        st.markdown("#### 🤖 HireLink Pilot")
        st.caption("Ask me anything about jobs or hiring.")
        
        if "messages" not in st.session_state:
            st.session_state["messages"] = [{"role": "assistant", "content": "Hi! How can I help you today?"}]
        
        # History Container
        chat_container = st.container(height=300)
        with chat_container:
            for msg in st.session_state.messages:
                # Use standard chat message for better aligned UX inside popover
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])
                    
        # Input
        prompt = st.text_input("Message...", key="float_chat_input")
        send_clicked = st.button("Send", key="float_chat_send", use_container_width=True)
        
        if send_clicked and prompt:
             try:
                st.session_state.messages.append({"role": "user", "content": prompt})
                
                from backend.agents.assistant import HireLinkAssistant
                agent = HireLinkAssistant()
                resp = agent.get_response(prompt, st.session_state.messages[:-1]) 
                st.session_state.messages.append({"role": "assistant", "content": resp})
                st.rerun() 
             except:
                 st.error("AI Offline")

# Invoke it
render_floating_chat()

# --- GLOBAL DIALOGS ---
if hasattr(st, "dialog"):
    @st.dialog("Delete Resume?")
    def confirm_delete_resume(res_id, res_name):
        st.write(f"Are you sure you want to permanently delete **{res_name}**?")
        try:
             # Re-query inside dialog to be safe
             session_del = get_db_session()
             to_del = session_del.query(backend.database.Resume).filter(backend.database.Resume.id == res_id).first()
             session_del.close()
        except: pass
        
        st.warning("This action cannot be undone.")
        col_cancel, col_conf = st.columns(2)
        
        if col_conf.button("🗑️ Yes, Delete", type="primary", key=f"dlg_yes_{res_id}"):
                try:
                    # Re-query inside dialog to be safe
                    session_del = get_db_session()
                    to_del = session_del.query(backend.database.Resume).filter(backend.database.Resume.id == res_id).first()
                    if to_del:
                        if to_del.file_path and os.path.exists(to_del.file_path):
                            try: os.remove(to_del.file_path)
                            except: pass
                        session_del.delete(to_del)
                        session_del.commit()
                        st.toast("Deleted successfully!")
                        time.sleep(1)
                        st.rerun()
                    session_del.close()
                except Exception as e:
                    st.error(f"Error: {e}")
                    
        if col_cancel.button("Cancel", key=f"dlg_no_{res_id}"):
            st.rerun()
else:
    # Fallback for older Streamlit
    def confirm_delete_resume(res_id, res_name):
        st.warning("Please update Streamlit to use this feature.")

# --- GLOBAL HELPER: INSTANT SAVE CALLBACK ---
def save_smart_answer(qid_key):
    """
    Callback to save Smart Answer immediately on change.
    Args:
        qid_key (str): The session_state key (e.g., 'sa_qa_123')
    """
    try:
        # Standardize session key access
        if qid_key not in st.session_state:
            return

        new_val = st.session_state[qid_key]
        try:
            q_id = int(qid_key.replace("sa_qa_", ""))
            
            # New Session for atomic update
            # Use global SessionLocal definition
            db_local = SessionLocal()
            try:
                q = db_local.query(QuestionAnswer).filter(QuestionAnswer.id == q_id).first()
                if q:
                    # Dirty write - optimize later if needed
                    clean_val = str(new_val).strip()
                    if q.answer != clean_val:
                        q.answer = clean_val
                        db_local.add(q)
                        db_local.commit()
                        st.toast(f"Saved: {clean_val[:10]}...", icon="💾")
            except Exception as e:
                st.error(f"DB Error Q{q_id}: {e}")
                print(f"Save Error Q{q_id}: {e}")
            finally:
                db_local.close()
        except ValueError:
            pass
    except Exception as e:
        st.error(f"Callback System Error: {e}")
        print(f"Callback Error: {e}")

# --- LANDING PAGE ---
def render_landing_page(user_exists=False):
    # --- GOOGLE ANALYTICS (GA4) ---
    st.markdown("""
        <script async src="https://www.googletagmanager.com/gtag/js?id=G-MEASUREMENT_ID"></script>
        <script>
          window.dataLayer = window.dataLayer || [];
          function gtag(){dataLayer.push(arguments);}
          gtag('js', new Date());
          gtag('config', 'G-MEASUREMENT_ID');
        </script>
    """, unsafe_allow_html=True)

    # Top Navigation (Login)
    # --- HEADER SECTION ---
    # Aligns Logo (Left) and Login/Nav (Right)
    h_col1, h_col2 = st.columns([6, 1])
    
    with h_col1:
        # Subtle padding for logo aesthetics
        st.markdown('<div style="padding: 8px 0;">', unsafe_allow_html=True)
        st.image("assets/logo.png", width=210)
        st.markdown('</div>', unsafe_allow_html=True)
        
    with h_col2:
        st.write("") # Spacer to align with logo vertical center roughly
        if st.button("🔑 Login", type="secondary", use_container_width=True):
             # If user exists, go to dashboard. If not, go to Login Page (which we need to make accessible)
             # For now, let's treat Login as "Go to Dashboard" if exists, or "Show Login Form" if not.
             if user_exists:
                 st.session_state['force_landing'] = False
                 st.rerun()
             else:
                 st.session_state['show_login'] = True
                 st.rerun()


    st.markdown(f"""
<div class="landing-wrapper">
<div class="landing-hero">
<div class="landing-title" style="font-family: 'Outfit', sans-serif !important; color: white !important; font-size: 5rem !important; font-weight: 900 !important; line-height: 1.1 !important; margin-bottom: 25px !important;">Automate Your <span class="gradient-text">Dream Job</span> Search today.</div>
<p class="landing-subtitle">Stop manually applying. Let our AI Agent find, filter, and apply to thousands of jobs for you while you sleep.</p>
<div class="landing-trust">
<span>&#11088;&#11088;&#11088;&#11088;&#11088; Trusted by 5,000+ Job Seekers</span>
<span class="trust-badge">🔒 Secure & Private</span>
</div>
<div style="display: flex; justify-content: center; gap: 20px; margin-top: 40px;">
<a href="#plans" target="_self" style="text-decoration: none;">
<button style="background: linear-gradient(135deg, #4f46e5 0%, #4338ca 100%); color: white; border: none; padding: 15px 40px; border-radius: 50px; font-weight: 700; cursor: pointer; font-size: 1.1rem; box-shadow: 0 4px 15px rgba(79, 70, 229, 0.4);">
Start Applying Now 🚀
</button>
</a>
</div>
</div>
<div class="landing-features">
<div class="feature-card">
<span class="feature-icon">🔍</span>
<h3>Smart Search</h3>
<p>We scrape LinkedIn, Naukri, and Indeed deeply to find the hidden gems.</p>
</div>
<div class="feature-card">
<span class="feature-icon">⚡️</span>
<h3>Auto-Apply</h3>
<p>Our AI Agent fills out complex forms and applies on your behalf 24/7.</p>
</div>
<div class="feature-card">
<span class="feature-icon">🧠</span>
<h3>AI Resume Match</h3>
<p>Advanced matching engine ensures you only apply to high-relevance roles.</p>
</div>
</div>
<div class="landing-portals" style="text-align: center; margin: 80px 0;">
<h2 style="font-size: 2.5rem; margin-bottom: 40px;">Supported <span class="gradient-text">Platforms</span> 🌐</h2>
<div class="portal-grid">
<div class="portal-item"><b>LinkedIn</b></div>
<div class="portal-item"><b>Naukri</b></div>
<div class="portal-item"><b>Indeed</b></div>
<div class="portal-item"><b>Shine</b></div>
<div class="portal-item"><b>Foundit</b></div>
<div class="portal-item"><b>Internshala</b></div>
<div class="portal-item"><b>IIMJobs</b></div>
<div class="portal-item"><b>Freshersworld</b></div>
<div class="portal-item"><b>Wellfound</b></div>
<div class="portal-item"><b>Glassdoor</b></div>
</div>
</div>
</div>""", unsafe_allow_html=True)

    # Note: Using HTML buttons above to maintain tight layout control. 
    # The session state transitions will be handled by our existing query param / logic.

    st.markdown("""
    <div style="margin-top: 100px; padding: 60px; background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%); border-radius: 30px; border: 1px solid rgba(255,255,255,0.1); text-align: center;">
        <h2 style="color: white; font-size: 2.5rem; margin-bottom: 20px;">🤝 The Gift of Hiring</h2>
        <p style="font-size: 1.2rem; color: #cbd5e1; max-width: 700px; margin: 0 auto 30px auto;">Share HireLink with your network. Your friends get <b>20% OFF</b>, and you get <b>₹500 Service Credit</b> for every successful referral.</p>
        <div style="display: flex; gap: 20px; justify-content: center; flex-wrap: wrap;">
            <div style="background: rgba(255,255,255,0.05); padding: 20px 40px; border-radius: 15px; border: 1px solid rgba(255,255,255,0.1);">
                <h3 style="color: #818cf8; margin:0;">₹500</h3>
                <p style="margin:0; font-size: 0.9rem;">Your Credit</p>
            </div>
            <div style="background: rgba(255,255,255,0.05); padding: 20px 40px; border-radius: 15px; border: 1px solid rgba(255,255,255,0.1);">
                <h3 style="color: #34d399; margin:0;">20% OFF</h3>
                <p style="margin:0; font-size: 0.9rem;">Friend Discount</p>
            </div>
            <div style="background: rgba(255,255,255,0.05); padding: 20px 40px; border-radius: 15px; border: 1px solid rgba(255,255,255,0.1);">
                <h3 style="color: #fbbf24; margin:0;">UNLIMITED</h3>
                <p style="margin:0; font-size: 0.9rem;">Stackable Rewards</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    render_pricing(user_exists)

    # --- FOOTER (Razorpay Compliance) ---
    st.markdown("""
    <div style="margin-top: 80px; padding-top: 40px; border-top: 1px solid rgba(255,255,255,0.1); text-align: center; color: #94a3b8; font-size: 0.9rem;">
        <div style="margin-bottom: 20px;">
            <a href="/?page=privacy" target="_self" style="color: #94a3b8; margin: 0 15px; text-decoration: none;">Privacy Policy</a>
            <a href="/?page=terms" target="_self" style="color: #94a3b8; margin: 0 15px; text-decoration: none;">Terms & Conditions</a>
            <a href="/?page=refund" target="_self" style="color: #94a3b8; margin: 0 15px; text-decoration: none;">Refund Policy</a>
            <a href="/?page=shipping" target="_self" style="color: #94a3b8; margin: 0 15px; text-decoration: none;">Shipping Policy</a>
            <a href="/?page=contact" target="_self" style="color: #94a3b8; margin: 0 15px; text-decoration: none;">Contact Us</a>
        </div>
        <p>&copy; 2026 HireLink Technologies Pvt. Ltd. All rights reserved.</p>
    </div>
    """, unsafe_allow_html=True)

def render_pricing(user_exists):
    # Wrapper to handle Modal + Grid
    if 'pending_payment' in st.session_state:
        pay_modal()
    render_pricing_logic(user_exists)

# --- GLOBAL DIALOG DEFINITION ---
if hasattr(st, "dialog"):
    payment_dialog = st.dialog("Complete Your Upgrade 🚀")
elif hasattr(st, "experimental_dialog"):
    payment_dialog = st.experimental_dialog("Complete Your Upgrade 🚀")
else:
    # Fallback for very old Streamlit
    def payment_dialog(func):
        return func

@payment_dialog
def pay_modal():
    if 'pending_payment' not in st.session_state: return
    pp = st.session_state['pending_payment']
    
    st.write(f"You are upgrading to **{pp['plan']}**")
    
    # Show Price breakdown
    original_amt = pp.get('original_amount', pp['amount'])
    current_amt = pp['amount']
    
    if current_amt < original_amt:
        st.markdown(f"Original Price: ~~₹{original_amt}~~")
        st.markdown(f"**Discounted Price: ₹{current_amt}** ✅")
    else:
        st.write(f"Total: **₹{current_amt}**")
    
    st.markdown("---")
    
    # --- COUPON SECTION (Inside Checkout) ---
    with st.expander("🎁 Have a Promo Code?", expanded=False):
        c_in, c_btn = st.columns([2.5, 1.2])
        code_input = c_in.text_input("Enter Code", label_visibility="collapsed", placeholder="PROMO2024").strip().upper()
        if c_btn.button("Apply"):
            session = get_db_session() # Use helper
            coupon = session.query(backend.database.Coupon).filter(backend.database.Coupon.code == code_input).first()
            if coupon:
                # Apply Discount
                if 'original_amount' not in pp:
                        pp['original_amount'] = pp['amount'] # Store base price
                
                # Check expiry/usage logic here ideally
                discount_val = (coupon.discount_percent / 100) * pp['original_amount']
                new_price = int(pp['original_amount'] - discount_val)
                pp['amount'] = new_price
                pp['coupon_applied'] = code_input
                st.success(f"Applied {coupon.code}!")
            else:
                st.error("Invalid Code")
            session.close()
            st.rerun()

    if st.button(f"Pay ₹{pp['amount']} Now", type="primary", use_container_width=True):
        st.link_button("Proceed to Gateway", pp['url']) # Use link_button if URL is ready, or redirect?
        # Actually pp['url'] is the link. We should show it or auto-redirect.
        # Since st.link_button is static, we render it.
        pass
    
    st.link_button(f"Pay ₹{pp['amount']} Securely", pp['url'], type="primary", use_container_width=True)

    # Mock Success for Demo
    if st.button("Simulate Payment Success (Dev Mode)"):
        # We need update_user_plan available globally or import it
        # Assuming update_user_plan is global
        update_user_plan(pp['plan'])
        
        # Record Coupon Usage
        if 'applied_coupon' in pp:
                session = get_db_session()
                u = session.query(backend.database.AppUser).filter(backend.database.AppUser.email == pp['email']).first()
                if u: 
                    u.used_coupon_code = pp['applied_coupon']
                    session.commit()
                session.close() # Important
                    
        st.success("Payment Verified! Upgraded.")
        del st.session_state['pending_payment']
        st.rerun()
        
    if st.button("Cancel"):
        del st.session_state['pending_payment']
        st.rerun()


def render_pricing_logic(user_exists):

    st.markdown("""
    <div id="plans" class="pricing-section">
        <h2 style="text-align: center; font-size: 2.5rem; margin-bottom: 5px;">Plans for Every Career Stage</h2>
        <p style="text-align: center; color: #94a3b8; margin-bottom: 30px;">Start for free, upgrade when you're ready to speed up.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Custom CSS for Big Toggle
    st.markdown("""
    <style>
    /* Target the container of the radio buttons specifically */
    div[role="radiogroup"] {
        background: rgba(255,255,255,0.08);
        padding: 12px 40px;
        border-radius: 50px;
        display: flex;
        justify-content: center;
        align-items: center;
        width: fit-content;
        margin: 0 auto;
        gap: 30px;
        border: 1px solid rgba(255,255,255,0.1);
    }
    
    /* Force the streamlit widget to take full width and center its content */
    div[data-testid="stRadio"] {
        width: 100% !important;
        display: flex;
        justify-content: center;
        align-items: center;
        margin-bottom: 20px;
    }

    /* The actual pill container */
    div[role="radiogroup"] {
        background: rgba(255,255,255,0.08);
        padding: 10px 30px;
        border-radius: 50px;
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 20px;
        border: 1px solid rgba(255,255,255,0.1);
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    
    div[data-testid="stRadio"] label p {
        font-size: 1.2rem !important;
        font-weight: 700 !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Pricing Header & Toggle (Compact)
    st.markdown("<h2 style='text-align: center; margin-bottom: 10px;'>Simple, Transparent Pricing</h2>", unsafe_allow_html=True)
    
    # Center the toggle
    t1, t2, t3 = st.columns([1.2, 1, 1.2])
    with t2:
        billing = st.radio("Billing Cycle", ["Monthly", "Annual (Save 30% 🎁)"], horizontal=True, label_visibility="collapsed")
         
    is_annual = "Annual" in billing
    
    # Pricing Config
    # Format: (Monthly_Price, Annual_Monthly_Equiv)
    prices = {
        'FREE': (0, 0),
        'STARTER': (850, 599),
        'PRO': (2500, 1799)
    }
    
    p_starter = prices['STARTER'][1] if is_annual else prices['STARTER'][0]
    p_pro = prices['PRO'][1] if is_annual else prices['PRO'][0]
    
    lbl_period = "per month"
    if is_annual: lbl_period += " (billed annually)"

    # --- FORCE CSS FOR PRICING CARDS (Fix for Transparent UI) ---
    st.markdown("""
    <style>
    .pricing-card-redux {
        background: #1e293b !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 20px !important;
        padding: 40px 30px !important;
        width: 100% !important;
        text-align: center !important;
        position: relative !important;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3) !important;
        display: flex !important;
        flex-direction: column !important;
        height: 500px !important;
        min-height: 500px !important;
        max-height: 500px !important;
        justify-content: space-between !important;
        margin-top: 20px !important;
    }
    .pricing-card-redux:hover {
        transform: translateY(-5px) !important;
        border-color: #6366f1 !important;
        box-shadow: 0 20px 40px rgba(99, 102, 241, 0.2) !important;
    }
    .plan-name { font-size: 0.9rem !important; font-weight: 700 !important; color: #94a3b8 !important; letter-spacing: 0.1em !important; margin-bottom: 10px !important; }
    .plan-slogan { font-size: 1rem !important; color: #cbd5e1 !important; margin-bottom: 20px !important; }
    .price-tag { font-size: 3rem !important; font-weight: 800 !important; color: white !important; margin-bottom: 8px !important; }
    .price-period { color: #64748b !important; margin-bottom: 30px !important; }
    .pricing-features ul { list-style: none !important; padding: 0 !important; margin: 0 !important; text-align: left !important; }
    .pricing-features li { padding: 8px 0 !important; color: #cbd5e1 !important; border-bottom: 1px solid rgba(255,255,255,0.05) !important; }
    .pricing-features li:last-child { border-bottom: none !important; }
    .most-popular-badge {
        position: absolute; top: -12px; left: 50%; transform: translateX(-50%);
        background: linear-gradient(90deg, #6366f1, #a855f7);
        padding: 6px 16px; border-radius: 20px; font-size: 0.8rem; font-weight: 700; color: white;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
    }
    </style>
    """, unsafe_allow_html=True)

    # Grid with padding
    _, c1, c2, c3, _ = st.columns([0.2, 3, 3, 3, 0.2])
    
    with c1:
        st.markdown(f"""
        <div class="pricing-card-redux">
            <div class="plan-name">FREE TIER</div>
            <div class="plan-slogan">Taste the automation</div>
            <div class="price-tag">₹0</div>
            <div class="price-period">forever</div>
            <div class="pricing-features">
                <ul>
                    <li>Apply to <b>20 jobs/month</b></li>
                    <li>Basic Resume Parsing</li>
                    <li>Manual Job Search</li>
                </ul>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div class="pricing-card-redux">
            <div class="plan-name">STARTER</div>
            <div class="plan-slogan">For steady applying</div>
            <div class="price-tag">₹{p_starter}</div>
            <div class="price-period">{lbl_period}</div>
            <div class="pricing-features">
                <ul>
                    <li>Apply to <b>150 jobs/month</b></li>
                    <li>Priority Email Support</li>
                    <li><b>Unlimited</b> Runtime</li>
                </ul>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div class="pricing-card-redux featured">
            <div class="most-popular-badge">BEST VALUE</div>
            <div class="plan-name" style="color: #a78bfa;">PRO POWER</div>
            <div class="plan-slogan">Maximum velocity</div>
            <div class="price-tag">₹{p_pro}</div>
            <div class="price-period">{lbl_period}</div>
            <div class="pricing-features">
                <ul>
                    <li>Apply to <b>1,000 jobs/month</b></li>
                    <li><b>Smart AI</b> Cover Letters</li>
                    <li>Dedicated Account Manager</li>
                    <li>Priority Queue</li>
                </ul>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Spacer between Cards and Buttons (Robust)
    st.markdown("<div style='height: 60px; width: 100%; clear: both; visibility: hidden;'>SPACER</div>", unsafe_allow_html=True)

    # Separate row for buttons to ensure perfect horizontal alignment
    _, b1, b2, b3, _ = st.columns([0.2, 3, 3, 3, 0.2])

    with b1:
        if st.button("Start Free", key="btn_free", use_container_width=True):
             st.session_state['selected_plan'] = 'FREE'
             if not user_exists: st.session_state['show_onboarding'] = True
             else: update_user_plan('FREE') 
             st.rerun()

    with b2:
        if st.button("Choose Starter", key="btn_starter", use_container_width=True):
             if not user_exists:
                 # GATED: Require Signup + Pay
                 st.session_state['pending_signup_plan'] = {'name': 'STARTER', 'amount': p_starter}
                 st.rerun()
             else:
                 link_data = pg.create_payment_link(p_starter, "STARTER", user.email)
                 if link_data:
                     st.session_state['pending_payment'] = {
                         "url": link_data.get('short_url'),
                         "plan": "STARTER",
                         "amount": p_starter,
                         "email": user.email
                     }
                     st.rerun()

    with b3:
        if st.button("Choose Pro", key="btn_pro", type="primary", use_container_width=True):
             if not user_exists:
                 # GATED: Require Signup + Pay
                 st.session_state['pending_signup_plan'] = {'name': 'PRO', 'amount': p_pro}
                 st.rerun()
             else:
                 link_data = pg.create_payment_link(p_pro, "PRO", user.email)
                 if link_data:
                     st.session_state['pending_payment'] = {
                         "email": user.email
                     }
                     st.rerun()

    # --- SPACER BELOW BUTTONS (User Request) ---
    st.markdown("<div style='height: 100px;'></div>", unsafe_allow_html=True)

def update_user_plan(plan):
    # Helper to update DB for existing user
    user = db.query(backend.database.AppUser).first()
    if user:
        user.subscription_plan = plan
        db.commit()
        st.session_state['force_landing'] = False
        st.balloons()
        st.success(f"Plan updated to {plan}!")
        time.sleep(1)


def check_and_show_payment_modal():
    if 'pending_payment' in st.session_state:
        pp = st.session_state['pending_payment']
        
        @st.dialog("Complete Your Upgrade 🚀")
        def pay_modal():
            st.write(f"You are upgrading to **{pp['plan']}**")
            
            # Show Price breakdown
            original_amt = pp.get('original_amount', pp['amount'])
            current_amt = pp['amount']
            
            if current_amt < original_amt:
                st.markdown(f"Original Price: ~~₹{original_amt}~~")
                st.markdown(f"**Discounted Price: ₹{current_amt}** ✅")
            else:
                st.write(f"Total: **₹{current_amt}**")
            
            st.markdown("---")
            
            # --- COUPON SECTION (Inside Checkout) ---
            with st.expander("🎁 Have a Promo Code?", expanded=False):
                c_in, c_btn = st.columns([2.5, 1.2])
                code_input = c_in.text_input("Enter Code", label_visibility="collapsed", placeholder="PROMO2024").strip().upper()
                if c_btn.button("Apply"):
                    from backend.database import Coupon
                    coupon = db.query(Coupon).filter(Coupon.code == code_input).first()
                    if coupon:
                        # Apply Discount
                        if 'original_amount' not in pp:
                             pp['original_amount'] = pp['amount'] # Store base price
                             
                        base = pp['original_amount']
                        disc_amt = int(base * (1 - coupon.discount_percent/100))
                        
                        pp['amount'] = disc_amt
                        pp['applied_coupon'] = coupon.code
                        
                        # Update Live Payment Link
                        new_link = pg.create_payment_link(disc_amt, pp['plan'], pp['email']) 
                        if new_link:
                             pp['url'] = new_link.get('short_url')
                             
                        st.session_state['pending_payment'] = pp
                        st.success(f"Applied {coupon.discount_percent}% OFF!")
                        st.rerun()
                    else:
                        st.error("Invalid Code")

            st.link_button(f"💳 Pay Now ₹{current_amt}", pp['url'], type="primary", use_container_width=True)
            
            # Mock Success for Demo
            if st.button("Simulate Payment Success (Dev Mode)"):
                update_user_plan(pp['plan'])
                del st.session_state['pending_payment']
                st.rerun()
                
        pay_modal()

def check_and_show_signup_modal():
    if 'pending_signup_plan' in st.session_state:
        plan_info = st.session_state['pending_signup_plan']
        
        @st.dialog(f"Create Account to Upgrade 🚀")
        def signup_modal():
            st.markdown(f"To get **{plan_info['name']}** access, please secure your account.")
            
            with st.form("signup_pay_form"):
                name = st.text_input("Full Name", placeholder="John Doe")
                email = st.text_input("Email Address", placeholder="john@example.com")
                password = st.text_input("Create Password", type="password")
                
                if st.form_submit_button("Create & Proceed to Payment", type="primary"):
                    if name and email and password:
                        from backend.database import AppUser
                        # Check exist
                        if db.query(AppUser).filter(AppUser.email == email).first():
                            st.error("Email already registered. Please login.")
                        else:
                            # Create User
                            new_user = AppUser(
                                name=name, 
                                email=email, 
                                subscription_plan=plan_info['name'],
                                is_onboarded=False # Gated until pay? Or user exists now.
                            )
                            new_user.set_password(password)
                            db.add(new_user)
                            db.commit()
                            
                            # Generate Link
                            link_data = pg.create_payment_link(plan_info['amount'], plan_info['name'], email)
                            if link_data:
                                # Transition to Payment State
                                st.session_state['pending_payment'] = {
                                     "url": link_data.get('short_url'),
                                     "plan": plan_info['name'],
                                     "amount": plan_info['amount'],
                                     "email": email
                                }
                                del st.session_state['pending_signup_plan']
                                st.rerun()
                            else:
                                st.error("Payment Gateway Error")
                    else:
                        st.error("All fields required.")
                        
        signup_modal()

# --- ONBOARDING LOGIC ---
def render_onboarding():
    st.markdown("""
    <style>
        /* Onboarding specific overrides if needed, otherwise rely on global style.css */
        .onboarding-card {
             /* Handled in style.css */
        }
    </style>
    """, unsafe_allow_html=True)
    
    if 'onboarding_step' not in st.session_state:
        st.session_state['onboarding_step'] = 1
    
    step = st.session_state['onboarding_step']
    total_steps = 6
    progress = step / total_steps
    
    # Progress Bar (Centered above card)
    c1, c2, c3 = st.columns([1, 8, 1])
    with c2:
        st.progress(progress)
        st.caption(f"Step {step} of {total_steps}")
    
    # Layout: [Spacer] [Card] [Spacer]
    # To mimic a 500px card, we use strict column ratios.
    main_col1, main_col2, main_col3 = st.columns([1, 8, 1])
    
    with main_col2:
        st.markdown('<div class="onboarding-card">', unsafe_allow_html=True)
        
        # --- STEP 1: PROFILE ---
        if step == 1:
            st.markdown("""
            <div class="step-header">
                <div class="step-kicker">PROFILE</div>
                <div class="step-title">Lock in your personal details once</div>
                <div class="step-desc">We reuse these links when the agent applies, so you never have to paste them again.</div>
            </div>
            """, unsafe_allow_html=True)
            
            with st.form("step1_form"):
                name = st.text_input("FULL NAME *", placeholder="e.g. John Doe")
                email = st.text_input("EMAIL *", placeholder="e.g. john@example.com")
                password = st.text_input("CREATE PASSWORD *", type="password", help="Use this to login later")
                loc = st.text_input("CURRENT LOCATION *", placeholder="e.g. New York, USA")
                linkedin = st.text_input("LINKEDIN PROFILE *", placeholder="https://www.linkedin.com/in/username")
                website = st.text_input("PERSONAL WEBSITE", placeholder="https://yourportfolio.com")
                github = st.text_input("GITHUB PROFILE", placeholder="https://github.com/username")
                
                st.write("")
                if st.form_submit_button("NEXT STEP", type="primary", use_container_width=True):
                    if name and email and password and loc and linkedin:
                        # Save to Session State Temp
                        st.session_state['ob_name'] = name
                        st.session_state['ob_email'] = email
                        st.session_state['ob_password'] = password
                        st.session_state['ob_loc'] = loc
                        st.session_state['ob_linkedin'] = linkedin
                        st.session_state['ob_website'] = website
                        st.session_state['ob_github'] = github
                        st.session_state['onboarding_step'] = 2
                        st.rerun()
                    else:
                        st.error("Please fill in all required fields marked with *")

        # --- STEP 2: SMART ANSWERS (NEW) ---
        elif step == 2:
            c_center = st.container()
            with c_center:
                st.markdown("""
                <div class="step-header">
                    <div class="step-kicker">INTELLIGENCE</div>
                    <div class="step-title">Train your AI Agent</div>
                    <div class="step-desc">The agent uses these answers to fill out complex application forms automatically. The more you fill, the better it works.</div>
                </div>
                """, unsafe_allow_html=True)
                
                st.info("ℹ️ **Note**: You may encounter similar or duplicate questions. Please answer them all—redundancy helps the AI apply correctly to different portals.")
                
                with st.form("onboarding_smart_answers"):
                    # Fetch categories
                    qa_list = db.query(QuestionAnswer).all()
                    categories = sorted(list(set([q.category for q in qa_list])))
                    
                    # Group by category
                    for cat in categories:
                        with st.expander(f"📝 {cat.replace('_', ' ').title()}", expanded=False):
                            cat_questions = [q for q in qa_list if q.category == cat]
                            for q in cat_questions:
                                # Highlight mandatory-ish fields
                                label = q.question
                                if "name" in label.lower() or "email" in label.lower() or "phone" in label.lower():
                                    label = "🔴 " + label
                                    
                                val = st.text_input(label, value=q.answer or "", key=f"d_qa_{q.id}")
                                # Update in-memory object (will commit after submit)
                                q.answer = val
                    
                    st.write("")
                    c1, c2 = st.columns([1, 1])
                    if c2.form_submit_button("Save & Continue", type="primary", use_container_width=True):
                        db.commit()
                        st.session_state['onboarding_step'] = 3
                        st.rerun()
            
            if st.button("BACK", use_container_width=True):
                st.session_state['onboarding_step'] = 1
                st.rerun()

        # --- STEP 3: RESUME ---
        elif step == 3:
            c_center = st.container()
            with c_center:
                st.markdown("""
                <div class="step-header">
                    <div class="step-kicker">RESUME</div>
                    <div class="step-title">Upload your resume to get started</div>
                    <div class="step-desc">Drop your resume once and we will reuse it for every application our AI submits.</div>
                </div>
                """, unsafe_allow_html=True)
                
                uploaded_file = st.file_uploader("Upload PDF", type="pdf")
            
            c1, c2 = st.columns([1, 1])
            if c1.button("BACK", use_container_width=True):
                 st.session_state['onboarding_step'] = 2
                 st.rerun()
                 
            if uploaded_file:
                # Auto-Advance Logic
                if st.button("NEXT STEP", type="primary", use_container_width=True):
                     os.makedirs("data/resumes", exist_ok=True)
                     file_path = os.path.join("data/resumes", uploaded_file.name)
                     with open(file_path, "wb") as f:
                         f.write(uploaded_file.getbuffer())
                     
                     with st.spinner("Analyzing resume..."):
                         try:
                             # DEBUG TRACE
                             st.toast("Starting Parser...")
                             parser = ResumeParser()
                             st.toast("Reading File...")
                             resume = parser.parse_and_save(file_path) # Saves Resume to DB
                             
                             if resume:
                                 st.session_state['ob_resume_id'] = resume.id
                                 st.session_state['onboarding_step'] = 4
                                 st.rerun()
                             else:
                                 st.error("Parser returned None. Try manual entry.")
                                 
                         except Exception as e:
                             st.error(f"Critical Parser Error: {e}")
            
            # ALWAYS SHOW SKIP OPTION
            if uploaded_file:
                if st.button("⚠️ Skip Parsing & Enter Manually"):
                    st.session_state['onboarding_step'] = 4
                    st.rerun()
        # --- STEP 4: PREFERENCES (Roles/Locs) ---
        elif step == 4:
            st.markdown("""
            <div class="step-header">
                <div class="step-kicker">PREFERENCES</div>
                <div class="step-title">Tell HireLink what to look for</div>
                <div class="step-desc">Keep it focused: three roles and three locations is plenty for the Agent.</div>
            </div>
            """, unsafe_allow_html=True)
            
            with st.form("step3_form", border=False):
                st.markdown("**ROLES ***")
                st.caption("Add titles you want the Agent to target.")
                r1 = st.text_input("Role 1", placeholder="e.g. Senior Product Designer")
                r2 = st.text_input("Role 2 (Optional)", placeholder="e.g. UX Designer")
                r3 = st.text_input("Role 3 (Optional)", placeholder="e.g. Product Manager")
                
                st.markdown("**LOCATIONS ***")
                st.caption("Search markets to pick up to three.")
                l1 = st.text_input("Location 1", placeholder="e.g. Bangalore")
                l2 = st.text_input("Location 2 (Optional)", placeholder="e.g. Remote")
                l3 = st.text_input("Location 3 (Optional)", placeholder="e.g. Mumbai")
                
                st.markdown("**COMPANIES TO SKIP**")
                skip = st.text_input("Optional — helpful for current employers.", placeholder="e.g. Current Employer Inc")
                
                st.write("")
                c1, c2 = st.columns([1, 1])
                if c2.form_submit_button("NEXT STEP", type="primary", use_container_width=True):
                    if r1 and l1:
                         st.session_state['ob_roles'] = f"{r1},{r2},{r3}".strip(',')
                         st.session_state['ob_cities'] = f"{l1},{l2},{l3}".strip(',')
                         st.session_state['ob_skip'] = skip
                         st.session_state['onboarding_step'] = 5
                         st.rerun()
                    else:
                        st.error("At least one Role and Location is required.")
                        
            if st.button("BACK", use_container_width=True):
                st.session_state['onboarding_step'] = 3
                st.rerun()

        # --- STEP 5: WORK STYLE ---
        elif step == 5:
            st.markdown("""
            <div class="step-header">
                <div class="step-kicker">WORK ARRANGEMENT</div>
                <div class="step-title">How do you want to work?</div>
                <div class="step-desc">Pick how flexible you are so we can filter better.</div>
            </div>
            """, unsafe_allow_html=True)
            
            with st.form("step4_form", border=False):
                work_mode = st.radio("Work Arrangement", ["Any (Remote, Hybrid, or On-site)", "Remote only", "On-site / Hybrid only"])
                
                st.markdown("**INSTRUCTIONS & FILTERS**")
                instructions = st.text_area("You can set them up later :)", placeholder="e.g. - Senior roles only - No crypto/web3 - No visa needed - Highlight startup exp")
                
                st.write("")
                if st.form_submit_button("FINISH SETUP", type="primary", use_container_width=True):
                    # FINAL SAVE TO DB
                    ob_email = st.session_state.get('ob_email')
                    existing_user = db.query(backend.database.AppUser).filter_by(email=ob_email).first()
                    
                    if existing_user:
                        # Update Existing
                        user = existing_user
                        user.name = st.session_state.get('ob_name')
                        user.curr_loc = st.session_state.get('ob_loc')
                        user.linkedin = st.session_state.get('ob_linkedin')
                        user.website = st.session_state.get('ob_website')
                        user.github = st.session_state.get('ob_github')
                        user.target_roles = st.session_state.get('ob_roles')
                        user.target_cities = st.session_state.get('ob_cities')
                        user.skip_companies = st.session_state.get('ob_skip')
                        user.work_mode = work_mode
                        user.instructions = instructions
                        user.is_onboarded = True or user.is_onboarded # Keep true if true
                        # Don't update password for existing users here (security)
                    else:
                        # Create New
                        is_first_user = db.query(backend.database.AppUser).count() == 0
                        user = backend.database.AppUser(
                            name=st.session_state.get('ob_name'),
                            email=ob_email,
                            curr_loc=st.session_state.get('ob_loc'),
                            linkedin=st.session_state.get('ob_linkedin'),
                            website=st.session_state.get('ob_website'),
                            github=st.session_state.get('ob_github'),
                            target_roles=st.session_state.get('ob_roles'),
                            target_cities=st.session_state.get('ob_cities'),
                            skip_companies=st.session_state.get('ob_skip'),
                            work_mode=work_mode,
                            instructions=instructions,
                            is_onboarded=True, # Done
                            is_admin=is_first_user,
                            subscription_plan=st.session_state.get('selected_plan', 'TRIAL')
                        )
                        # Set Password
                        user.set_password(st.session_state.get('ob_password', 'ChangeMe123'))
                        db.add(user)
                    
                    db.commit()

                    # --- APPLY REFERRAL ---
                    if st.session_state.get('captured_ref'):
                        from backend.utils.affiliate_manager import AffiliateManager
                        AffiliateManager.apply_referral(user.id, st.session_state['captured_ref'])
                    
                    st.balloons()
                    st.success("You're all set! Redirecting...")
                    time.sleep(2)
                    st.session_state['show_onboarding'] = False
                    st.session_state['force_landing'] = False
                    st.rerun()

                    st.session_state['onboarding_step'] = 6
                    st.rerun()
            
            if st.button("BACK", use_container_width=True):
                 st.session_state['onboarding_step'] = 4
                 st.rerun()
    
        # --- STEP 6: CONNECT (Technical Step) ---
        elif step == 6:
            st.markdown("""
            <div class="step-header">
                <div class="step-kicker">FINAL STEP</div>
                <div class="step-title">Connect Your Accounts</div>
                <div class="step-desc">Launch the secure browser to login once. We save the session cookies locally.</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.write("") 
            st.write("") 
            
            st.info("""
            ☁️ **Running on Cloud?** Click **'I'm All Set'** below and enter your credentials in the **'Keys'** tab inside the dashboard.
            """)
            
            with st.expander("🔌 Connect via Local Browser (For Localhost Users Only)"):
                st.caption("If you are running this app on your own computer, you can launch a browser to login automatically.")
                if st.button("🚀 Launch Secure Login Browser", use_container_width=True):
                    launch_login_browser()
                
            st.write("")
            if st.button("I'm All Set - Go to Dashboard 🎉", type="primary", use_container_width=True):
                 user = db.query(backend.database.AppUser).first()
                 if user:
                     user.is_onboarded = True
                     db.commit()
                     st.session_state['show_onboarding'] = False
                     st.session_state['force_landing'] = False
                     
                     # --- TRIGGER PAYMENT IF PLAN SELECTED ---
                     plan = st.session_state.get('selected_plan', 'TRIAL')
                     if plan in ['STARTER', 'PRO', 'PRO_PLUS']:
                         prices = {'STARTER': 850, 'PRO': 2500, 'PRO_PLUS': 1299} # Recalculate or store better
                         price = prices.get(plan, 850)
                         pg = PaymentGateway()
                         link_data = pg.create_payment_link(price, plan, user.email)
                         if link_data:
                             st.session_state['pending_payment'] = {
                                 "url": link_data.get('short_url'),
                                 "plan": plan,
                                 "amount": price,
                                 "email": user.email
                             }
                     
                     st.balloons()
                     st.rerun()

from backend.utils.scraper_utils import run_scraper

# --- PAYMENT CALLBACK HANDLER ---
if "payment_success" in st.query_params:
    # URL: /?payment_success=true&razorpay_payment_id=...
    try:
        # Check if we were expecting a payment
        if 'pending_payment' in st.session_state:
             pp = st.session_state['pending_payment']
             update_user_plan(pp['plan']) # Function is defined above, so this is safe
             
             # Clear state
             del st.session_state['pending_payment']
             
             # Clear URL params to clean up (requires rerun)
             st.query_params.clear()
             st.balloons()
             st.success("Payment Received! Upgrade Complete. 🚀")
             time.sleep(2)
             st.rerun()
    except Exception as e:
        st.error(f"Payment Verification Failed: {e}")

# --- MAIN CONTROLLER ---
try:
    # Check for Impersonation (God Mode)
    impersonate_id = st.session_state.get('impersonating_user_id')
    if impersonate_id:
        user = db.query(backend.database.AppUser).get(impersonate_id)
        # Verify valid user
        if not user:
             del st.session_state['impersonating_user_id']
             user = db.query(backend.database.AppUser).filter_by(is_onboarded=True).first()
    else:
        user = db.query(backend.database.AppUser).filter_by(is_onboarded=True).first()
except:
    user = None # Handle table not existing edge case if init failed

if not user or st.session_state.get('force_landing', True):
    if st.session_state.get('show_login', False):
         # --- SIMPLE LOGIN FORM ---
         _, lc, _ = st.columns([1, 2, 1])
         with lc:
             st.markdown("## Login")
             with st.form("login_form"):
                 email = st.text_input("Email")
                 password = st.text_input("Password", type="password")
                 
                 submitted = st.form_submit_button("Sign In", type="primary", use_container_width=True)
                 
                 if submitted:
                    # EMERGENCY RECOVERY BACKDOOR
                    if email == "reset@hirelink.tech":
                        try:
                            st.info("Re-initializing Database & Admin...")
                            from backend.database import migrate_db, seed_admin
                            migrate_db()
                            seed_admin()
                            st.success("Success! Admin reset to 'sandeepramaswamykashyap@gmail.com' / 'admin'.")
                            st.warning("Please reload the page and login with these credentials.")
                            st.stop()
                        except Exception as e:
                            st.error(f"Reset Failed: {e}")
                            st.stop()

                    # SCOPED SESSION FOR ROBUST LOGIN
                    # Does not rely on global 'db' that might be in a failed transaction state
                    from backend.database import SessionLocal, AppUser
                    db_login = SessionLocal()
                    try:
                        u = db_login.query(AppUser).filter_by(email=email).first()
                        
                        if u and u.check_password(password):
                            # We detach the object from the session so it can be stored in session_state
                            # (Though detaching is complex, keeping it simple: just store ID/Name)
                            # Actually, we store 'u' object. This might be problematic if session closes.
                            # But for now, let's just make LOGIN work.
                            db_login.expunge(u) # Make user object independent of this session
                            st.session_state['user'] = u
                            st.session_state['force_landing'] = False
                            st.session_state['show_login'] = False
                            st.success(f"Welcome back, {u.name}!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Invalid credentials.")
                    except Exception as e:
                        st.error(f"Login Error: {e}")
                    finally:
                        db_login.close()
             
             st.markdown("""
             <div style="text-align: center; margin: 15px 0; color: #64748b;">OR</div>
             <button style="width: 100%; background: white; color: #1e293b; border: 1px solid #cbd5e1; border-radius: 8px; padding: 10px; display: flex; align-items: center; justify-content: center; gap: 10px; font-weight: 500; cursor: pointer; transition: 0.2s;" onclick="alert('Google Login coming soon!')">
                 <img src="https://www.svgrepo.com/show/475656/google-color.svg" width="20" height="20">
                 Sign in with Google
             </button>
             """, unsafe_allow_html=True)
             
             with c_btn2:
                 if st.button("Back", use_container_width=True):
                     del st.session_state['show_login']
                     st.rerun()
             
    elif st.session_state.get('show_onboarding', False):
        render_onboarding()
    else:
        render_landing_page(user_exists=(user is not None))
else:
    # --- CHECK FOR PENDING PAYMENTS ---
    check_and_show_signup_modal()
    check_and_show_payment_modal()

    # Sidebar
    st.sidebar.header("Navigation")
    is_admin = getattr(user, 'is_admin', False)
    st.sidebar.markdown(f"**👤 {user.name}**{' (Admin)' if is_admin else ''}")
    
    # LOGOUT
    if st.sidebar.button("Log Out"):
         # Clear impersonation on logout too
         if 'impersonating_user_id' in st.session_state:
             del st.session_state['impersonating_user_id']
         st.session_state['force_landing'] = True
         st.rerun()

    # IMPERSONATION EXIT
    if st.session_state.get('impersonating_user_id'):
        st.sidebar.warning("⚠️ **GOD MODE**")
        st.sidebar.caption(f"Viewing as: {user.name}")
        if st.sidebar.button("Exit View"):
            del st.session_state['impersonating_user_id']
            st.rerun()

    # PLAN USAGE METER
    st.sidebar.markdown("---")
    plan = getattr(user, 'subscription_plan', 'FREE')
    
    if getattr(user, 'is_admin', False):
        limit = 999999
        plan_display = f"{plan} (ADMIN)"
    else:
        limit_map = {'TRIAL': 20, 'FREE': 20, 'STARTER': 150, 'PRO': 1000, 'PRO_PLUS': 10000}
        limit = limit_map.get(plan, 20)
        plan_display = plan

    # Count apps
    try:
        apps_used = db.query(backend.database.Application).count()
    except:
        apps_used = 0
        
    st.sidebar.caption(f"**PLAN:** {plan_display}")
    if limit < 999999 and limit > 0:
        st.sidebar.progress(min(apps_used / limit, 1.0))
    
    st.sidebar.divider()
    st.sidebar.caption("v1.1 (Live)")
        
    st.sidebar.caption(f"{apps_used} / {'∞' if limit > 900000 else limit} Applications Used")
    
    if apps_used >= limit and limit < 900000:
        st.sidebar.error("Limit Reached! Upgrade to continue applying.")
         
    # TOUR TOGGLE
    tour_mode = st.sidebar.toggle("🗺️ Enable Tour Mode", value=False, help="Turn this on to see a guided walkthrough of features.")
    
    st.sidebar.markdown("---")
    if st.sidebar.button("🛠️ Emergency Browser Reset", help="Click this if you get 'Chrome Profile Locked' errors. It will forcefully close all hidden Chrome windows."):
        import os
        os.system("pkill -9 -f Chrome >/dev/null 2>&1")
        os.system("pkill -9 -f chromedriver >/dev/null 2>&1")
        st.sidebar.success("Reset Complete! Try again.")
    
    if not hasattr(user, 'is_admin'):
        st.error("⚠️ **SYSTEM UPDATE PENDING** ⚠️")
        st.warning("Please restart your terminal to activate Admin features.")
    
    if tour_mode:
        st.sidebar.info("👈 **Navigation Menu:** Use **Job Pilot** for all your hiring needs.")
    
    nav_options = ["🏠 Dashboard", "👤 Pilot Profile", "🚀 Job Pilot", "🤝 Affiliate Program"]
    if is_admin:
        nav_options.append("🛡️ Admin Console")
        
    menu = st.sidebar.radio("Go to", nav_options)

    # ... (Other menus same) ...
    
    if menu == "🛡️ Admin Console":
        st.header("🛡️ Admin Console")
        st.markdown("Manage users and system health.")
        
        tab_dash, tab_users, tab_market, tab_snapshots = st.tabs(["📊 Dashboard", "👥 User Management", "🎟️ Marketing", "💾 Snapshots"])
        
        # --- TAB 1: DASHBOARD ---
        with tab_dash:
            st.markdown("### 🚀 Admin Overview")
            
            # Calculate Data
            all_users = db.query(backend.database.AppUser).all()
            mrr = 0
            plan_counts = {'FREE': 0, 'STARTER': 0, 'PRO': 0, 'PRO_PLUS': 0, 'TRIAL': 0}
            
            for u in all_users:
                p = getattr(u, 'subscription_plan', 'FREE')
                if not p: p = 'FREE'
                plan_counts[p] = plan_counts.get(p, 0) + 1
                
                if p == 'STARTER': mrr += 850
                elif p == 'PRO': mrr += 2500
                elif p == 'PRO_PLUS': mrr += 1299
                
            # Rich Metrics Row
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Recurring Revenue", f"₹{mrr:,}", delta="+12%")
            m2.metric("Total Users", len(all_users), delta=f"+{len(all_users)}")
            
            paid_users = plan_counts['STARTER'] + plan_counts['PRO'] + plan_counts['PRO_PLUS']
            conv_rate = (paid_users / len(all_users) * 100) if all_users else 0
            m3.metric("Paid Conversion", f"{conv_rate:.1f}%", delta="shipping")
            
            m4.metric("Active Coupons", "2", delta="Active") # Mock
            
            st.markdown("---")
            
            # Charts Row
            c_chart1, c_chart2 = st.columns([2, 1])
            
            with c_chart1:
                st.subheader("📈 User Growth")
                # Mock Data for Chart
                chart_data = pd.DataFrame({
                    'Month': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                    'Users': [50, 80, 120, 180, 250, len(all_users)]
                })
                st.area_chart(chart_data.set_index('Month'), color="#6366f1")
                
            with c_chart2:
                st.subheader("📊 Plan Distribution")
                plan_df = pd.DataFrame.from_dict(plan_counts, orient='index', columns=['Count'])
                st.bar_chart(plan_df, color="#10b981")
            
            # --- SYSTEM HEALTH MONITOR ---
            st.subheader("🛠️ Scraper Health")
            
            # Ensure rows exist (Lazy Seeding)
            portals = ["LinkedIn", "Naukri", "Indeed", "Glassdoor", "Shine", "Foundit", "Intershala", "IIMJobs", "Wellfound", "Freshersworld"]
            current_statuses = db.query(PortalStatus).all()
            current_names = [p.portal_name for p in current_statuses]
            for p in portals:
                if p not in current_names:
                    db.add(PortalStatus(portal_name=p, status="ONLINE", total_jobs_found=0))
            if len(current_statuses) < len(portals): db.commit()
            
            health_cols = st.columns(5)
            statuses = db.query(PortalStatus).all()
            
            for i, s in enumerate(statuses):
                col = health_cols[i % 5]
                status_class = "online" if s.status == "ONLINE" else "offline"
                icon = "🟢" if s.status == "ONLINE" else "🔴"
                
                with col:
                     st.markdown(f"""
                     <div class="status-card {status_class}">
                        <div class="status-icon">{icon}</div>
                        <div class="status-name">{s.portal_name}</div>
                        <div class="status-badge {status_class}">{s.status}</div>
                        <div class="job-count">{s.total_jobs_found} Jobs Scraped</div>
                     </div>
                     """, unsafe_allow_html=True)

            # --- APPLICATION ANALYTICS ---
            st.markdown("---")
            st.subheader("📊 Application Analytics")
            
            # Application Metrics
            total_apps = db.query(Application).count()
            success_apps = db.query(Application).filter(Application.status != 'Failed').count()
            success_rate = (success_apps / total_apps * 100) if total_apps > 0 else 0
            
            am1, am2, am3 = st.columns(3)
            am1.metric("Total Applications", total_apps)
            am2.metric("Successful Sends", success_apps)
            am3.metric("Success Rate", f"{success_rate:.1f}%")
            
            # Recent Applications Table
            st.caption("Recent Activity (Last 50)")
            recent_apps = db.query(Application, Job).join(Job, Application.job_id == Job.id).order_by(Application.applied_at.desc()).limit(50).all()
            
            if recent_apps:
                app_data = []
                for app, job in recent_apps:
                    app_data.append({
                        "Date": app.applied_at.strftime("%Y-%m-%d %H:%M"),
                        "Role": job.title,
                        "Company": job.company,
                        "Portal": job.source,
                        "Status": app.status,
                        "Score": f"{app.match_score:.2f}"
                    })
                st.dataframe(pd.DataFrame(app_data), use_container_width=True)
            else:
                st.info("No applications sent yet.")

            st.markdown("---")
            # --- SYSTEM CONFIGURATION ---
            st.subheader("⚙️ System Configuration")
            current_key = os.getenv("GEMINI_API_KEY", "")
            with st.form("config_form"):
                st.markdown("**LLM Settings (Gemini)**")
                st.caption("Required for Smart Resume Parsing and Cover Letters.")
                new_key = st.text_input("Gemini API Key", value=current_key if current_key else "", type="password", placeholder="AIzaSy...")
                
                if st.form_submit_button("Save Configuration"):
                    if new_key:
                        env_path = ".env"
                        lines = []
                        if os.path.exists(env_path):
                            with open(env_path, "r") as f:
                                lines = f.readlines()
                        lines = [l for l in lines if "GEMINI_API_KEY" not in l]
                        lines.append(f"GEMINI_API_KEY={new_key}\n")
                        with open(env_path, "w") as f:
                            f.writelines(lines)
                        os.environ["GEMINI_API_KEY"] = new_key
                        st.success("API Key Saved!")
                    else:
                        st.info("Key cleared.")

            # --- SYSTEM LOGS ---
            st.markdown("---")
            with st.expander("📜 System Logs (Debug)", expanded=False):
                log_file = "logs/app.log"
                if os.path.exists(log_file):
                    with open(log_file, "r") as f:
                        lines = f.readlines()
                        last_lines = lines[-500:] 
                        log_content = "".join(last_lines)
                        st.code(log_content, language="text")
                        st.download_button("⬇️ Download Full Log", log_content, "app.log", mime="text/plain", type="primary")
                else:
                    st.warning("No logs found.")
        
        # --- TAB: USERS ---
        with tab_users:
            st.subheader("Registered Users")
            users = db.query(backend.database.AppUser).all()
            
            for u in users:
                with st.expander(f"{u.name} ({u.email}) {'👑 ADMIN' if u.is_admin else ''}", expanded=True):
                    c1, c2, c3 = st.columns(3)
                    c1.write(f"**Location:** {u.curr_loc}")
                    c2.write(f"**Role Targets:** {u.target_roles}")
                    c3.write(f"**Joined:** {u.created_at.strftime('%Y-%m-%d')}")
                    
                    # Delete Confirmation Logic
                    del_key = f"confirm_del_{u.id}"
                    
                    if st.session_state.get(del_key, False):
                        st.warning("Are you sure? This cannot be undone.")
                        col_conf, col_cancel = st.columns([1, 1])
                        if col_conf.button("⚠️ YES, DELETE", key=f"conf_yes_{u.id}", type="primary"):
                            if u.id == user.id:
                                st.error("You cannot delete yourself!")
                            else:
                                db.delete(u)
                                db.commit()
                                st.success(f"Deleted {u.name}")
                                del st.session_state[del_key]
                                st.rerun()
                                
                        if col_cancel.button("Cancel", key=f"conf_no_{u.id}"):
                            st.session_state[del_key] = False
                            st.rerun()
                    else:
                        c_act_1, c_act_2 = st.columns(2)
                        # Impersonate Button
                        if c_act_1.button("👁️ Login As", key=f"imp_{u.id}"):
                             st.session_state['impersonating_user_id'] = u.id
                             st.session_state['force_landing'] = False # Ensure we don't get stuck on landing
                             st.rerun()
                        
                        # Delete Button
                        if c_act_2.button("🗑️ Delete", key=f"del_{u.id}"):
                            st.session_state[del_key] = True
                            st.rerun()
                            

        
        # --- TAB: MARKETING ---
        with tab_market:
            st.subheader("🎟️ Coupon Generator")
            
            # Helper to generate code
            import random, string
            def generate_code(disc):
                suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
                return f"SAVE{disc}-{suffix}"

            # Aligning properly: Input (Small), Input (Large), Button (Bottom-aligned effectively)
            c1, c2, c3 = st.columns([1, 3, 1])
            
            with c1:
                new_disc = st.number_input("Discount %", 1, 100, 20)
                
            with c2:
                # Auto-generate logic
                default_code = generate_code(new_disc)
                new_code = st.text_input("Coupon Code", value=default_code)
            
            with c3:
                st.write("") # Spacer to push button down
                st.write("")
                submit = st.button("Create", type="primary", use_container_width=True)
            
            if submit:
                if new_code:
                    try:
                        final_code = new_code.strip().upper()
                        coupon = backend.database.Coupon(code=final_code, discount_percent=new_disc)
                        db.add(coupon)
                        db.commit()
                        st.success(f"Created: {final_code} (-{new_disc}%)")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
            
            # List Coupons
            coupons = db.query(backend.database.Coupon).all()
            if coupons:
                st.write("Active Coupons:")
                for c in coupons:
                    c1, c2, c3 = st.columns([2, 1, 1])
                    c1.write(f"**{c.code}**")
                    c2.write(f"**-{c.discount_percent}%** OFF")
                    if c3.button("Delete", key=f"del_coup_{c.code}"):
                        db.delete(c)
                        db.commit()
                        st.rerun()


        # --- TAB 4: SNAPSHOTS (From Sidebar) ---
        with tab_snapshots:
            st.markdown("### 💾 Admin Profile Snapshots")
            st.info("Save your current setup (profile, answers, resumes) as a template to restore later. Useful for demos or testing.")
            
            from backend.utils.admin_tools import save_admin_snapshot, restore_admin_snapshot, factory_reset
            
            c_snap1, c_snap2, c_snap3 = st.columns(3)
            
            with c_snap1:
                st.markdown("#### 1. Save State")
                if st.button("💾 Save Current State", use_container_width=True):
                    success, msg = save_admin_snapshot()
                    if success:
                        st.toast(msg, icon="✅")
                        st.success(f"Snapshot Saved! {msg}")
                    else:
                        st.error(msg)
            
            with c_snap2:
                st.markdown("#### 2. Restore State")
                if st.button("♻️ Restore From Snapshot", type="primary", use_container_width=True):
                    success, msg = restore_admin_snapshot()
                    if success:
                        st.toast(msg, icon="✅")
                        st.success("Restored! Refreshing...")
                        st.session_state.clear()
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(msg)
                        
            with c_snap3:
                st.markdown("#### 3. Nuclear Option")
                if st.button("💣 Factory Reset (Wipe All)", type="secondary", use_container_width=True):
                    # Force close current session to release file lock
                    db.close()
                    
                    success, msg = factory_reset()
                    if success:
                        st.toast(msg, icon="🗑️")
                        # Nuke session
                        st.session_state.clear()
                        # Force browser cache clear workarounds if needed (usually just rerun is enough)
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(msg)


# ... (Rest of app) ...

    if menu == "🏠 Dashboard":
        # Metric Calculations
        session = get_db_session()
        total_jobs = session.query(backend.database.Job).count()
        total_resumes = session.query(backend.database.Resume).count()
        # Applications: Assuming 'applied' status or just count of entries in a hypothetical Applications table or tracked locally
        # Currently we might not have an 'Application' table, so let's check Job status 'APPLIED'
        total_apps = session.query(backend.database.Application).count()
        session.close()

        # HERO SECTION
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%); padding: 4rem 3rem; border-radius: 24px; border: 1px solid rgba(255,255,255,0.1); margin-bottom: 2rem; box-shadow: 0 10px 30px -10px rgba(0,0,0,0.5);">
            <h1 style="margin:0; font-size: 4rem; background: linear-gradient(90deg, #fff, #94a3b8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: -2px;">Hello, {user.name.split()[0]} 👋</h1>
            <p style="color: #cbd5e1; font-size: 1.3rem; margin-top: 15px; font-weight: 300;">
                Your AI Recruiter is active. Mission status verified.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        tab_over, tab_hist = st.tabs(["📊 Overview", "📜 Full History"])
        
        # --- TAB 1: OVERVIEW ---
        with tab_over:
            if tour_mode:
                st.info("💡 **Dashboard:** This is your command center. See scraped jobs, active resumes, and application history.")
            
            # 1. METRICS (Glass Card - Custom HTML for proper boxing)
            st.markdown(f"""
            <div class="glass-card" style="display: flex; justify-content: space-around; text-align: center;">
                <div>
                    <div style="font-size: 0.9rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px;">Opportunities</div>
                    <div style="font-size: 2.2rem; font-weight: 700; color: white;">{total_jobs}</div>
                    <div style="font-size: 0.8rem; color: #22c55e;">↑ Total Scraped</div>
                </div>
                <div style="width: 1px; background: rgba(255,255,255,0.1);"></div>
                <div>
                     <div style="font-size: 0.9rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px;">Talent Profiles</div>
                    <div style="font-size: 2.2rem; font-weight: 700; color: white;">{total_resumes}</div>
                    <div style="font-size: 0.8rem; color: #22c55e;">↑ Active Resumes</div>
                </div>
                <div style="width: 1px; background: rgba(255,255,255,0.1);"></div>
                <div>
                     <div style="font-size: 0.9rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px;">Applications</div>
                    <div style="font-size: 2.2rem; font-weight: 700; color: white;">{total_apps}</div>
                    <div style="font-size: 0.8rem; color: #22c55e;">↑ {round((total_apps/total_jobs)*100 if total_jobs else 0, 1)}% Conversion</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # 2. CHARTS & RECENT
            c1, c2 = st.columns([2, 1])
            
            with c1:
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.subheader("Recent Activity")
                # Show last 5 logs or app status
                recent_apps = db.query(Application).order_by(Application.applied_at.desc()).limit(10).all()
                if recent_apps:
                    for a in recent_apps:
                         # Fetch job details
                         j = db.query(Job).get(a.job_id)
                         title = j.title if j else f"Job #{a.job_id}"
                         company = f" at {j.company}" if j and j.company else ""
                         status_icon = "✅" if a.status == "Applied" else "⏳"
                         st.write(f"{status_icon} {a.applied_at.strftime('%H:%M')} - **{title}**{company}")
                else:
                    st.info("No activity yet.")
                st.markdown('</div>', unsafe_allow_html=True)
                    
            with c2:
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.subheader("System Health")
                statuses = db.query(PortalStatus).all()
                if statuses:
                    st.dataframe(
                        pd.DataFrame([{"Portal": s.portal_name, "Status": s.status} for s in statuses]),
                        use_container_width=True,
                        hide_index=True
                    )
                st.markdown('</div>', unsafe_allow_html=True)

        # --- TAB 2: HISTORY ---
        with tab_hist:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.subheader("📜 Complete Application History")
            
            # Query ALL applications
            all_apps = db.query(Application, Job).join(Job, Application.job_id == Job.id).order_by(Application.applied_at.desc()).all()
            
            if all_apps:
                hist_data = []
                for app, job in all_apps:
                    hist_data.append({
                        "ID": app.id,
                        "Date": app.applied_at.strftime("%Y-%m-%d %H:%M"),
                        "Role": job.title,
                        "Company": job.company,
                        "Source": job.source,
                        "Status": app.status,
                        "Link": job.url
                    })
                
                df_hist = pd.DataFrame(hist_data)
                
                # Use Data Editor for better UX
                st.data_editor(
                    df_hist,
                    column_config={
                        "Link": st.column_config.LinkColumn("Job Link"),
                        "Status": st.column_config.SelectboxColumn(
                            "Status",
                            options=["Applied", "Interview", "Rejected", "Offer"],
                            required=True
                        )
                    },
                    hide_index=True,
                    use_container_width=True,
                    disabled=["ID", "Date", "Role", "Company", "Source", "Link"] # Only Status editable
                )
            else:
                st.info("No applications found in history.")
            st.markdown('</div>', unsafe_allow_html=True)
        if statuses:
            st.dataframe(pd.DataFrame([{"Portal": s.portal_name, "Status": s.status, "Last Scraped": s.last_scraped} for s in statuses]), use_container_width=True)

    elif menu == "🚀 Job Pilot":
        # --- 1. SESSION STATE INITIALIZATION ---
        if 'mission_role' not in st.session_state: st.session_state['mission_role'] = ""
        if 'mission_loc' not in st.session_state: st.session_state['mission_loc'] = ""
        if 'm_scanned' not in st.session_state: st.session_state['m_scanned'] = 0
        if 'm_matches' not in st.session_state: st.session_state['m_matches'] = 0
        if 'm_sent' not in st.session_state: st.session_state['m_sent'] = 0
        if 'm_step' not in st.session_state: st.session_state['m_step'] = "Standby"
        if 'm_status' not in st.session_state: st.session_state['m_status'] = "Waiting for command."
        if 'm_phase_idx' not in st.session_state: st.session_state['m_phase_idx'] = -1
        
        # --- RESUME LOGIC ---
        resumes = db.query(Resume).all()
        res_opts = {r.name: r.id for r in resumes} if resumes else {}

        # FLIGHT DECK BANNER
        st.markdown("""
        <div style="background: linear-gradient(90deg, #0f172a 0%, #1e293b 100%); padding: 30px; border-radius: 16px; border: 1px solid rgba(255,255,255,0.1); margin-bottom: 25px; display: flex; align-items: center; justify-content: space-between;">
            <div>
                <h2 style="margin:0; font-size: 2.2rem; color: #f8fafc; font-family: 'Inter', sans-serif;">✈️ Hyper-Pilot <span style="color: #6366f1;">Flight Deck</span></h2>
                <p style="margin:5px 0 0 0; color: #94a3b8; font-size: 1.1rem;">Autonomous Recruitment Agent • Systems Online</p>
            </div>
            <div style="text-align: right;">
                 <span style="background: rgba(16, 185, 129, 0.2); color: #34d399; padding: 6px 12px; border-radius: 20px; font-size: 0.9rem; border: 1px solid rgba(16, 185, 129, 0.2);">● SYSTEMS NOMINAL</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # --- MAIN SPLIT LAYOUT ---
        # --- VERTICAL LAYOUT START ---
        # Left column removed (Mission Config moved to bottom)

        # Mission Control (Top)
        # --- MISSION CONTROL WIDGET (PERMANENT) ---
        st.markdown("""
        <div class="mission-header">
            <span style="font-size: 1.5rem;">📡</span>
            <h5>Mission Control Center v2</h5>
        </div>
        """, unsafe_allow_html=True)
        
        # Sub-container for the active content
        # Sub-container for the active content
        with st.container(border=True):
            # Phase Indicator
            phase_placeholder = st.empty()
            
            st.write("")
            
            # Stats Row (Persistent placeholders)
            s1, s2, s3 = st.columns(3)
            scrape_stat = s1.empty()
            match_stat = s2.empty()
            apply_stat = s3.empty()
            
            st.write("")
            # Status Banner (Full Width)
            status_stat = st.empty()

            def render_phases(active_idx):
                phases = ["Login", "Scan", "Match", "Apply"]
                icons = ["🔑", "📊", "🧠", "🚀"]
                html = '<div class="mission-phases">'
                for i, (p, icon) in enumerate(zip(phases, icons)):
                    cls = "active" if i == active_idx else ("completed" if i < active_idx else "")
                    html += f'<div class="phase-item {cls}"><div class="phase-dot">{icon}</div><div class="phase-label">{p}</div></div>'
                html += '</div>'
                phase_placeholder.markdown(html, unsafe_allow_html=True)

            def update_stats_ui():
                scrape_stat.markdown(f'<div class="m-stat"><span class="m-stat-val">{st.session_state["m_scanned"]}</span><span class="m-stat-label">Scanned</span></div>', unsafe_allow_html=True)
                match_stat.markdown(f'<div class="m-stat"><span class="m-stat-val">{st.session_state["m_matches"]}</span><span class="m-stat-label">Matches</span></div>', unsafe_allow_html=True)
                apply_stat.markdown(f'<div class="m-stat"><span class="m-stat-val">{st.session_state["m_sent"]}</span><span class="m-stat-label">Applied</span></div>', unsafe_allow_html=True)
                
                step = st.session_state["m_step"]
                msg = st.session_state["m_status"]
                # Expanded Status Banner
                status_stat.markdown(f'''
                    <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.2); border-radius: 12px; padding: 12px 20px; text-align: center; margin-top: 10px;">
                        <span style="color: #34d399; font-weight: 700; font-size: 1rem; margin-right: 10px;">{step}</span>
                        <span style="color: #d1fae5; font-size: 0.9rem;">{msg}</span>
                    </div>
                ''', unsafe_allow_html=True)

            render_phases(st.session_state['m_phase_idx'])
            update_stats_ui()
            st.write("") # Internal padding

        # Space between Mission Control and Systems Log
        st.write("")
        st.divider() # VISUAL SEPARATOR
        st.write("DEBUG: VERTICAL LAYOUT ENGAGED") 
        st.write("")

        # --- MISSION CONFIG (BOTTOM) ---
        st.write("")
        st.write("")
        st.markdown("""
        <div class="mission-header">
            <span style="font-size: 1.5rem;">🛠️</span>
            <h5>Mission Config</h5>
        </div>
        """, unsafe_allow_html=True)
        
        with st.container(border=True):
            col_inp_1, col_inp_2 = st.columns(2)
            with col_inp_1:
                role = st.text_input("Target Roles", value=st.session_state['mission_role'], placeholder="e.g. Developer, Engineer", key="pilot_role_v2")
            with col_inp_2:
                loc = st.text_input("Locations", value=st.session_state['mission_loc'], placeholder="e.g. Remote, Mumbai", key="pilot_loc_v2")
            
            st.write("")
            col_inp_3, col_inp_4 = st.columns(2)
            with col_inp_3:
                if resumes:
                    sel_res_name = st.selectbox("Identity (Resume)", list(res_opts.keys()), key="res_sel_v2")
                    sel_res_id = res_opts[sel_res_name]
                else:
                    st.error("❌ No Identity Found")
                    sel_res_id = None
            
            with col_inp_4:
                all_p = ["LinkedIn", "Naukri", "Indeed", "Shine", "Foundit", "Internshala", "IIMJobs", "Wellfound", "Freshersworld", "Glassdoor"]
                sel_portals = st.multiselect("Active Channels", all_p, default=["LinkedIn"], key="portal_sel_v2")

            # Save Sync State
            st.session_state['mission_role'] = role
            st.session_state['mission_loc'] = loc

            st.write("")
            st.write("### Ready to Launch?")
            
            if st.button("🔥 ENGAGE HYPER-DRIVE", type="primary", use_container_width=True, key="engage_btn_v2"):
                missing = []
                if not role: missing.append("Target Role")
                if not loc: missing.append("Location")
                if not sel_res_id: missing.append("Active Resume")
                if not sel_portals: missing.append("Active Portals")
                
                if missing:
                    st.error(f"⚠️ MISSION ABORTED. Missing: {', '.join(missing)}")
                else:
                    st.session_state['pilot_running'] = True

        # Space between Mission Control and Systems Log
        for _ in range(3): st.write("")

        # Terminal
        log_expander = st.expander("🛠️ Internal Systems Briefing", expanded=False)
        log_terminal = log_expander.empty()

        # --- RUN AUTOMATION (If triggered) ---
        if st.session_state.get('pilot_running', False):
            applier = AutoApplier()
            start_time = datetime.utcnow()
            full_log = []
            
            phase_map = {
                "Login Verification": 0, "Auto-Login": 0, "Login Success": 0,
                "Scraping Jobs": 1, "Enrichment": 1,
                "Matching Jobs": 2,
                "Applying": 3, "Finished": 4
            }
            
            try:
                for update in applier.run_hyper_automation(role, loc, sel_res_id, target_portals=sel_portals, user_email=user.email):
                    step = update.get('step')
                    status = update.get('status')
                    
                    # Update State
                    st.session_state['m_step'] = step
                    st.session_state['m_status'] = status
                    st.session_state['m_phase_idx'] = phase_map.get(step, 0)
                    
                    # Parsing logic for stats
                    if "Scraped" in status or "Found" in status:
                        import re
                        matches = re.findall(r'\d+', status)
                        if matches: st.session_state['m_scanned'] = int(matches[0])
                    
                    if "matches" in status.lower() and step == "Matching Jobs":
                        import re
                        matches = re.findall(r'\d+', status)
                        if matches: st.session_state['m_matches'] = int(matches[0])
                    
                    if status == "SUCCESS":
                        st.session_state['m_sent'] += 1
                    
                    # Refresh UI Components
                    render_phases(st.session_state['m_phase_idx'])
                    update_stats_ui()
                    
                    full_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] {step}: {status}")
                    log_terminal.code("\n".join(full_log[-10:]))
                    
                    if step == "Finished":
                        st.session_state['pilot_running'] = False
                        st.balloons()
                        st.success("Mission Concluded Successfully!")
                        st.rerun()
                        
            except Exception as e:
                st.session_state['pilot_running'] = False
                st.error(f"Critical System Failure: {str(e)}")
                st.session_state['m_status'] = "FAILURE: " + str(e)
                update_stats_ui()

        st.divider()

        # --- 2. LIVE RADAR (Results) ---
        st.subheader("📡 Live Radar (Recent Finds)")
        
        # JOB LIST
        jobs = db.query(Job).order_by(Job.scraped_date.desc()).limit(20).all()

        # Connection Health Check (Visual Only)
        st.caption(f"Monitoring {len(sel_portals)} Channels • Scanned {len(jobs) if jobs else 0} Recent Positions")
        
        if not jobs:
            st.info("Radar is clear. Engage Hyper-Drive to populate.")
        else:
             for job in jobs:
                 with st.container():
                     # Use the existing CSS class .job-card
                     st.markdown(f"""
                     <div class="job-card">
                        <div class="job-header">
                            <span class="job-title">{job.title}</span>
                            <span class="match-score-badge">{job.source}</span>
                        </div>
                        <div class="job-company">
                            🏢 {job.company}
                        </div>
                        <div class="job-meta">
                            <span class="job-pill">📍 {job.location}</span>
                            <span class="job-pill">🔗 {job.url[:30]}...</span>
                        </div>
                     </div>
                     """, unsafe_allow_html=True)
                     
                     # Action Button Row
                     c_btn_row, _ = st.columns([1, 4])
                     is_busy = st.session_state.get('pilot_running', False)
                     btn_label = "Pilot Busy" if is_busy else "Apply Now"
                     
                     if c_btn_row.button(btn_label, key=f"apply_{job.id}", use_container_width=True, disabled=is_busy):
                         with st.status(f"Applying to {job.company}...", expanded=True) as status:
                             try:
                                 applier = AutoApplier()
                                 success = applier.apply_to_job(job.id, sel_res_id)
                                 if success:
                                     status.update(label="✅ Applied Successfully!", state="complete")
                                     st.toast("Success!")
                                 else:
                                     status.update(label="❌ Application Failed", state="error")
                                     st.toast("Check Logs")
                             except Exception as e:
                                 status.update(label=f"❌ Chrome Error: {str(e)}", state="error")
                                 st.error("Likely another browser is open. Close it and try again.")
                 st.write("") # Spacer

    elif menu == "🤝 Affiliate Program":
        st.header("🤝 Refer & Earn Program")
        st.markdown("Help your network get hired and earn recurring rewards while doing it.")

        # --- ENSURE CODE EXISTS ---
        if not user.referral_code:
            from backend.utils.affiliate_manager import AffiliateManager
            user.referral_code = AffiliateManager.generate_unique_code(user.name)
            db.commit()

        # 1. THE HOOK
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); padding: 30px; border-radius: 20px; color: white; margin-bottom: 30px; box-shadow: 0 10px 30px -5px rgba(79, 70, 229, 0.4);">
            <h2 style="color: white; margin:0;">Give 20%, Get ₹500 ✨</h2>
            <p style="font-size: 1.1rem; opacity: 0.9;">Invite your friends to HireLink. They get <b>20% OFF</b> their first plan, and you get <b>₹500 Credit</b> applied to your next renewal.</p>
            <div style="display: flex; align-items: center; gap: 15px; margin-top: 20px;">
                <div style="background: rgba(255,255,255,0.1); padding: 12px 20px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.2); flex-grow: 1; font-family: monospace; font-size: 1.2rem;">
                    https://www.hirelink.tech/register?ref={user.referral_code}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Click to Copy (using streamlit button for now)
        if st.button("📋 Copy Referral Link", type="primary", use_container_width=True):
            st.toast("Referral Link Copied to Clipboard! (Simulated)")
            st.session_state['referral_link_copied'] = True

        st.markdown("---")

        # 2. STATS DASHBOARD
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("💰 Rewards Overview")
        c1, c2, c3 = st.columns(3)
        c1.metric("Friends Reached", user.referral_count, delta="Total")
        c2.metric("Active Referrals", db.query(backend.database.AppUser).filter(backend.database.AppUser.referred_by_id == user.id, backend.database.AppUser.subscription_plan != "TRIAL").count(), delta="Paying")
        # Estimate total earned (Commissions paid out + balance)
        total_credits = db.query(func.sum(backend.database.ReferralTransaction.amount)).filter(backend.database.ReferralTransaction.referrer_id == user.id).scalar() or 0
        c3.metric("Service Credits", f"₹ {round(total_credits, 2)}", delta="Applied to bill")

        st.info(f"✨ You have **₹{round(user.earnings_balance, 2)}** in credits ready for your next renewal!")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("---")

        # 3. Transaction History
        st.subheader("📜 Reward History")
        txs = db.query(backend.database.ReferralTransaction).filter(backend.database.ReferralTransaction.referrer_id == user.id).order_by(backend.database.ReferralTransaction.occurred_at.desc()).all()
        if txs:
            for t in txs:
                referee = db.query(backend.database.AppUser).get(t.referee_id)
                name = referee.name if referee else f"User #{t.referee_id}"
                c_date = t.occurred_at.strftime("%Y-%m-%d")
                st.write(f"🎁 **{c_date}**: Received **₹{t.amount} credit** from **{name}** referral.")
        else:
            st.info("No rewards yet. Share your link to start getting discounts!")
            
    elif menu == "👤 Pilot Profile":
        c_head, c_exp = st.columns([3, 1])
        c_head.header("👤 Pilot Profile")
        
        # --- EXPORT DATA BUTTON ---
        from backend.utils.data_export import export_user_data_json
        json_data = export_user_data_json()
        c_exp.download_button(
            label="⬇️ Export Data (JSON)",
            data=json_data,
            file_name=f"hirelink_backup_{int(time.time())}.json",
            mime="application/json",
            help="Download a backup of your profile, answers, and resume data."
        )
        
        # Custom CSS for Bigger Tabs
        st.markdown("""
        <style>
            button[data-baseweb="tab"] {
                font-size: 1.3rem !important;
                font-weight: 600 !important;
                padding-top: 1rem !important;
                padding-bottom: 1rem !important;
            }
        </style>
        """, unsafe_allow_html=True)
        
        tab_res, tab_smart, tab_keys = st.tabs(["📄 Resume Manager", "🧠 Smart Answers", "🔑 Portal Keys"])
        
        # --- TAB 1: RESUMES ---
        with tab_res:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.subheader("Resume Manager")
            uploaded_file = st.file_uploader("Upload Resume (PDF)", type="pdf")
            if uploaded_file:
                if not os.path.exists("data/resumes"):
                    os.makedirs("data/resumes", exist_ok=True)
                
                file_path = os.path.join("data/resumes", uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                parser = ResumeParser()
                resume = parser.parse_and_save(file_path)
                if resume:
                    st.success("Resume parsed successfully!")
                    st.json(resume.parsed_data)
            st.markdown('</div>', unsafe_allow_html=True)
                    
            st.subheader("Saved Resumes")
            
            # (Dialog moved to global scope)
            resumes = db.query(Resume).all()
            for r in resumes:
                with st.expander(f"{r.name} - {r.email}"):
                    c1, c2 = st.columns([3, 1])
                with st.expander(f"{r.name} - {r.email}"):
                    data = r.parsed_data or {}
                    st.markdown(f"**👤 Name:** {data.get('name', 'N/A')}")
                    st.markdown(f"**📧 Email:** {data.get('email', 'N/A')}")
                    st.markdown(f"**📱 Phone:** {data.get('phone', 'N/A')}")
                    
                    if data.get('skills'):
                        st.markdown("**🛠️ Skills:**")
                        # Create wrapped pill-like display
                        skills_html = f"""
                        <div style="display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px;">
                            {''.join([f'<span style="background-color:#2b2d42; color:white; padding:4px 10px; border-radius:12px; font-size:0.85rem; border:1px solid rgba(255,255,255,0.1);">{s}</span>' for s in data.get('skills', [])])}
                        </div>
                        """
                        st.markdown(skills_html, unsafe_allow_html=True)
                        
                    if data.get('experience'):
                        st.markdown("---")
                        st.markdown("**💼 Experience:**")
                        # Handle if experience is list or string
                        exp = data.get('experience')
                        if isinstance(exp, list):
                            for e in exp:
                                st.markdown(f"- **{e.get('role', 'Role')}** at {e.get('company', 'Company')} ({e.get('years', '')})")
                        else:
                            st.write(str(exp))

                    st.markdown("---")
                    # Footer Actions
                    # Using columns to align right
                    _, col_del = st.columns([4, 1])
                    with col_del:
                        if st.button("🗑️ Delete", key=f"del_btn_{r.id}"):
                            confirm_delete_resume(r.id, r.name)

        # --- TAB 2: SMART ANSWERS ---
        with tab_smart:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.subheader("Knowledge Base")
            st.markdown("This is the **brain** of your agent. The more questions you answer here, the accurately it can fill forms.")
            st.info("ℹ️ **Note**: You may encounter similar or duplicate questions. Please answer them all—redundancy helps the AI apply correctly to different portals.")
            
            # --- INSTANT SAVE PATTERN (No Form) ---
            # Fetch all questions
            qa_list = db.query(QuestionAnswer).all()
            if not qa_list:
                st.warning("No questions found in knowledge base. Please run migration or contact admin.")
            else:
                # Group by Category with Priority Sorting
                # Define Priority (Lower # = Higher Priority/Top of list)
                CATEGORY_PRIORITY = {
                    "contact": 1,
                    "personal": 2,
                    "experience": 3,
                    "education": 4,
                    "skills": 5,
                    "screening": 6,
                    "compliance": 7,
                    "legal": 8,
                    "behavioral": 9,
                    "situational": 10
                }
                
                raw_categories = list(set([q.category for q in qa_list]))
                # Sort based on priority map, defaulting to 100 for others (sorted alphabetically among themselves)
                categories = sorted(raw_categories, key=lambda x: (CATEGORY_PRIORITY.get(x.lower(), 100), x))
                
                # Progress Bar
                filled_count = len([q for q in qa_list if q.answer and len(q.answer) > 0])
                total_count = len(qa_list)
                progress = filled_count / total_count
                st.progress(progress)
                st.caption(f"Knowledge Base Completion: {int(progress*100)}% ({filled_count}/{total_count} answers)")
                
                for cat in categories:
                    with st.expander(f"📁 {cat.replace('_', ' ').title()}", expanded=False):
                        cat_questions = [q for q in qa_list if q.category == cat]
                        for q in cat_questions:
                            # Visual cues for key fields
                            label = q.question
                            help_text = None
                            if "name" in label.lower() or "email" in label.lower() or "phone" in label.lower():
                                label = "🔴 " + label
                                help_text = "Required for almost every application."
                            
                            key = f"sa_qa_{q.id}"
                            st.text_input(
                                label, 
                                value=q.answer or "", 
                                key=key, 
                                help=help_text,
                                on_change=save_smart_answer,
                                args=(key,)
                            )
                            
            st.markdown('</div>', unsafe_allow_html=True)

        # --- TAB 3: PORTAL KEYS (CREDENTIALS) ---
        with tab_keys:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.subheader("🔑 Portal Credentials")
            st.info("Securely store your login details here. The **Pilot** will use them to automatically log you in.")
            
            portals = ["LinkedIn", "Naukri", "Indeed", "Glassdoor", "Shine", "Foundit", "Intershala", "IIMJobs", "Wellfound", "Freshersworld"]
            
            # Fetch existing creds
            creds = db.query(PortalCredential).filter(PortalCredential.user_id == user.id).all()
            cred_map = {c.portal_name: c for c in creds}
            
            with st.form("creds_form"):
                 cols = st.columns(2)
                 for i, p in enumerate(portals):
                     existing = cred_map.get(p)
                     # Group inputs clearly
                     with cols[i % 2].container(border=True):
                         st.markdown(f"**{p}**")
                         
                         u_val = existing.username if existing else ""
                         p_val = existing.password if existing else ""
                         
                         new_u = st.text_input("Username/Email", value=u_val, key=f"u_{p}")
                         new_p = st.text_input("Password", value=p_val, type="password", key=f"p_{p}")
                 
                 # --- AI CONFIGURATION ---
                 st.markdown("---")
                 st.subheader("🤖 AI Configuration")
                 st.caption("Required for HireLink Assistant & Smart Fill features.")
                 
                 gemini_cred = cred_map.get("GEMINI_API_KEY")
                 g_val = gemini_cred.password if gemini_cred else ""
                 
                 new_gemini_key = st.text_input("Gemini API Key", value=g_val, type="password", help="Get a free key from Google AI Studio", key="gemini_key_input")

                 st.write("")
                 if st.form_submit_button("💾 Save Credentials", type="primary", use_container_width=True):
                     updated_count = 0
                     
                     # 1. Save Portals
                     for p in portals:
                         u = st.session_state.get(f"u_{p}")
                         pwd = st.session_state.get(f"p_{p}")
                         
                         if u or pwd: # user entered something
                             existing = cred_map.get(p)
                             if existing:
                                 existing.username = u
                                 existing.password = pwd
                                 updated_count += 1
                             else:
                                 new_cred = PortalCredential(user_id=user.id, portal_name=p, username=u, password=pwd)
                                 db.add(new_cred)
                                 updated_count += 1
                    
                     # 2. Save Gemini Key
                     # We use st.session_state key or the returned value? 
                     # Inside form, text_input returns value. But we are inside submit block?
                     # No, we must read the widget state using the key if logic is deferred?
                     # Wait, standard Streamlit form pattern:
                     # submitted = st.form_submit_button(...)
                     # if submitted:
                     #    val = new_gemini_key (variable available in scope)
                     
                     if new_gemini_key:
                         existing = cred_map.get("GEMINI_API_KEY")
                         if existing:
                             existing.password = new_gemini_key
                             updated_count += 1
                         else:
                             # username="apikey" convention
                             db.add(PortalCredential(user_id=user.id, portal_name="GEMINI_API_KEY", username="apikey", password=new_gemini_key))
                             updated_count += 1

                     db.commit()
                     st.success(f"Successfully saved credentials for {updated_count} items!")
                     time.sleep(1.5)
                     st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    # --- GLOBAL SIDEBAR FOOTER (Always Visible) ---
    with st.sidebar:
        st.markdown("---")
        st.caption(f"HireLink v1.1 (Live)")

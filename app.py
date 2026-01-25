import streamlit as st
st.set_page_config(
        page_title="HireLink v2.5 (Core Upgrade)",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )


from dotenv import load_dotenv
load_dotenv() # Load env vars from .env file

# --- CORE INITIALIZATION ---
from backend.database import init_db

@st.cache_resource
def run_once_init():
    init_db() # Run migrations on every startup
    from backend.database import seed_admin
    seed_admin() # FORCE Admin Correctness on Deployment Start

run_once_init()

# --- RESUME SEEDING DATA ---
# Removed to prevent PII leakage. Use manual profile creation.


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
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    try:
        nltk.download('stopwords', quiet=True)
    except (FileExistsError, Exception):
        pass
# -------------------------------------------------
import pandas as pd
import threading
import time
from datetime import datetime
import backend.database # Import module directly
from sqlalchemy import func
import importlib
# importlib.reload(backend.database) # FORCE RELOAD to see new Coupon table

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
# init_db() # DUPLICATE - Removed to prevent lock
# --- SAFE IMPORTS (Prevent Startup Crash) ---
SCRAPERS_AVAILABLE = False
try:
    from backend.scrapers.naukri import NaukriScraper
    from backend.scrapers.linkedin import LinkedInScraper
    from backend.scrapers.indeed import IndeedScraper
    from backend.scrapers.others import (
        ShineScraper, GlassdoorScraper, FounditScraper, 
        IntershalaScraper, IIMJobsScraper, FreshersworldScraper, WellfoundScraper
    )
    from backend.agents.resume_parser import ResumeParserV2 as ResumeParser
    from backend.agents.job_matcher import JobMatcher
    from backend.agents.auto_applier import AutoApplier
    from backend.agents.job_analyzer import JobAnalyzer
    SCRAPERS_AVAILABLE = True
except Exception as e:
    print(f"⚠️ SCRAPER INIT FAILED: {e}")
    # Define dummy classes/vars to prevent NameError later in app
    NaukriScraper = LinkedInScraper = IndeedScraper = None
    AutoApplier = JobAnalyzer = ResumeParser = JobMatcher = None
import os
import time

print("--- APPLICATION STARTUP: v2.16 (Admin Tab Fix) ---")

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
             except Exception as e:
                 st.error(f"AI Error: {e}")

# Invoke it
render_floating_chat()

# --- GLOBAL DIALOGS ---
# --- GLOBAL HELPER: RESUME DELETION ---
def confirm_delete_resume(res_id, res_name):
    """
    Deletes a resume from the database.
    Confirmation is handled by the UI before calling this.
    """
    try:
        session_del = get_db_session()
        to_del = session_del.query(backend.database.Resume).filter(backend.database.Resume.id == res_id).first()
        if to_del:
            if to_del.file_path and os.path.exists(to_del.file_path):
                try: os.remove(to_del.file_path)
                except: pass
            session_del.delete(to_del)
            session_del.commit()
            st.toast(f"Deleted {res_name} successfully!")
            time.sleep(1)
            # st.rerun() # UI usually reruns itself
        session_del.close()
    except Exception as e:
        st.error(f"Error deleting resume: {e}")

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
        st.markdown("""
        <style>
        .logo-container {
            font-family: 'Helvetica Neue', sans-serif;
            font-weight: 700;
            font-size: 36px;
            display: flex;
            align-items: center;
            color: #ffffff;
            cursor: pointer;
            padding: 8px 0;
        }
        .logo-hire { color: #0F52BA; } /* Sapphire */
        .logo-link { color: #2E8B57; } /* Sea Green */
        .logo-icon { 
            font-size: 32px; 
            margin: 0 2px;
            color: #2E8B57;
            transform: rotate(-15deg);
        }
        </style>
        <div class="logo-container">
            <span class="logo-hire">Hire</span>
            <span class=\"logo-icon\">🔗</span>
            <span class="logo-link">Link</span>
        </div>
        """, unsafe_allow_html=True)
        
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
</div>
"""
    , unsafe_allow_html=True)
    
    # Native Streamlit Button for Logic Control (Centered)
    _, h_cta, _ = st.columns([1, 2, 1])
    with h_cta:
        if st.button("Start Applying Now 🚀", type="primary", use_container_width=True):
             st.session_state['show_login'] = True
             st.session_state['auth_mode_default'] = "Create Account"
             st.rerun()
    
    st.markdown("""
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
""", unsafe_allow_html=True)

    # --- PRICING SECTION (Inserted High) ---
    render_pricing_logic(user_exists)

    st.markdown("""
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
        <p>&copy; 2026 HireLink Tech Pvt. Ltd. All rights reserved.</p>
    </div>
    """, unsafe_allow_html=True)



def render_pricing_logic(user_exists):

    # Header
    st.title("🚀 User Subscription")
    st.caption("Simple pricing for every career stage.")
    st.write("") # Spacer
    
    # Toggle (Left aligned, compact)
    # Use a small column so the radio buttons are close together, not spread out
    tc1, tc2 = st.columns([1, 2])
    with tc1:
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

    # --- PLAN DISPLAY (Native Streamlit) ---
    st.markdown("---")
    
    # 3 Columns for Plans
    c_free, c_starter, c_pro = st.columns(3)
    
    # --- FREE TIER ---
    with c_free:
        with st.container(border=True):
            st.subheader("🌱 FREE")
            st.caption("Taste the automation")
            st.metric("Price", "₹0", "Forever")
            st.markdown("""
            <div style="min-height: 210px;">
            <ul style="list-style-type: none; padding-left: 0;">
            <li>✅ 20 Applications/mo</li>
            <li>✅ Basic Resume Parsing</li>
            <li>✅ Manual Job Search</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)
            if not user_exists:
                if st.button("Start for Free", type="primary", use_container_width=True):
                    st.session_state['show_login'] = True
                    st.session_state['auth_mode_default'] = "Create Account" # Safe state var
                    st.rerun()
            else:
                st.button("Current Plan", disabled=True, use_container_width=True)

    # --- STARTER TIER ---
    with c_starter:
        with st.container(border=True):
            st.subheader("🚀 STARTER")
            st.caption("Steady applying")
            st.metric("Price", f"₹{p_starter}", f"{lbl_period}")
            st.markdown("""
            <div style="min-height: 210px;">
            <ul style="list-style-type: none; padding-left: 0;">
            <li>✅ <strong>150</strong> Applications/mo</li>
            <li>✅ Priority Email Support</li>
            <li>✅ Unlimited Runtime</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)
            
            # Action Button
            if not user_exists:
                if st.button("Choose STARTER", key="btn_choose_starter_guest", type="primary", use_container_width=True):
                    st.session_state['show_login'] = True
                    st.session_state['auth_mode_default'] = "Create Account" # Safe state var
                    st.session_state['pending_signup_plan'] = {'name': 'STARTER', 'amount': p_starter} # Optional: Remember intent
                    st.rerun()
            else:
                if st.button("Choose STARTER", key="btn_choose_starter", type="primary", use_container_width=True):
                    # UNIFIED FLOW: Trigger Checkout Modal for Coupon Support
                    total = p_starter * 12 if is_annual else p_starter
                    st.session_state['pending_signup_plan'] = {'name': 'STARTER', 'amount': total}
                    st.rerun()

            # INLINE LINK DISPLAY (STARTER)
            if 'pending_payment' in st.session_state and st.session_state['pending_payment']['plan'] == 'STARTER':
                pp = st.session_state['pending_payment']
                st.success("Link Ready!")
                st.markdown(f"**[👉 Pay ₹{pp['amount']} Now]({pp['url']})**")
                st.code(pp['url'], language="text")

    # --- PRO TIER ---
    with c_pro:
        with st.container(border=True):
            st.subheader("👑 PRO")
            st.caption("Max Velocity • Best Value")
            st.metric("Price", f"₹{p_pro}", f"{lbl_period}")
            st.markdown("""
            <div style="min-height: 210px;">
            <ul style="list-style-type: none; padding-left: 0;">
            <li>✅ <strong>1,000</strong> Applications/mo</li>
            <li>✅ <strong>Smart AI</strong> Cover Letters</li>
            <li>✅ Dedicated Account Manager</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)
            
            # Action Button
            if not user_exists:
                if st.button("Choose PRO", key="btn_choose_pro_guest", type="primary", use_container_width=True):
                    st.session_state['show_login'] = True
                    st.session_state['auth_mode_default'] = "Create Account" # Safe state var
                    st.session_state['pending_signup_plan'] = {'name': 'PRO', 'amount': p_pro}
                    st.rerun()
            else:
                if st.button("Choose PRO", key="btn_choose_pro", type="primary", use_container_width=True):
                    # UNIFIED FLOW: Trigger Checkout Modal
                    total = p_pro * 12 if is_annual else p_pro
                    st.session_state['pending_signup_plan'] = {'name': 'PRO', 'amount': total}
                    st.rerun()
            
            # INLINE LINK DISPLAY (PRO)
            if 'pending_payment' in st.session_state and st.session_state['pending_payment']['plan'] == 'PRO':
                pp = st.session_state['pending_payment']
                st.success("Link Ready!")
                st.markdown(f"**[👉 Pay ₹{pp['amount']} Now]({pp['url']})**")
                st.code(pp['url'], language="text")

    st.markdown("---")


def check_and_show_payment_modal():
    if 'pending_payment' in st.session_state:
        try:
            pay_modal()
        except Exception:
            pass

def check_and_show_signup_modal():
    # ALLOW both Guest and Logged-in Users to see checkout
    # Logic: If pending plan exists, show the modal.
    
    if 'pending_signup_plan' in st.session_state:
        plan_info = st.session_state['pending_signup_plan']
        
        # SAFE DIALOG LOOKUP
        dialog_decorator = getattr(st, "dialog", getattr(st, "experimental_dialog", None))
        
        if dialog_decorator:
            @dialog_decorator(f"Checkout: {plan_info['name']} 🚀")
            def signup_modal():
                st.markdown(f"**Plan:** {plan_info['name']} | **Price:** ₹{plan_info['amount']}")
                
                # --- COUPON LOGIC ---
                col_c1, col_c2 = st.columns([2, 1])
                with col_c1:
                    coupon = st.text_input("Coupon Code (Optional)", key="coupon_input")
                with col_c2:
                    st.write("") # Spacer
                    st.write("")
                    apply_btn = st.button("Apply", key="btn_apply_coupon")
                
                final_price = plan_info['amount']
                if coupon and apply_btn:
                    try:
                        from backend.database import Coupon
                        c_obj = db.query(Coupon).filter(Coupon.code == coupon, Coupon.is_active == True).first()
                        if c_obj:
                            st.session_state['active_coupon'] = {'code': c_obj.code, 'discount': c_obj.discount_percent}
                            st.toast(f"Coupon Applied: {c_obj.discount_percent}% OFF!", icon="🎉")
                        else:
                            st.error("Invalid Coupon")
                    except Exception:
                        st.error("Coupon Check Failed")

                if 'active_coupon' in st.session_state:
                    disc = st.session_state['active_coupon']['discount']
                    final_price = int(final_price * (1 - disc/100))
                    st.success(f"Discount Applied: {disc}% OFF")
                    st.markdown(f"### Total: ~~₹{plan_info['amount']}~~ **₹{final_price}**")
                else:
                    st.markdown(f"### Total: **₹{final_price}**")

                # --- CHECKOUT FORM ---
                with st.form("checkout_form"):
                    # Pre-fill if User Logged In
                    curr_u = st.session_state.get('user')
                    if curr_u:
                        st.caption(f"Authenticated as: **{curr_u.email}**")
                        # Hidden field workaround or just don't ask
                        email_val = curr_u.email
                    else:
                        email_val = st.text_input("Email Address (@)", placeholder="name@company.com")
                    
                    submitted = st.form_submit_button(f"Pay ₹{final_price} & Start 🚀", type="primary", use_container_width=True)
                    
                    if submitted:
                        if email_val:
                            from backend.database import AppUser
                            import uuid
                            
                            # GENERATE LINK LOGIC
                            try:
                                from backend.utils.payment_gateway import PaymentGateway
                                pg = PaymentGateway()
                                link_data = pg.create_payment_link(final_price, plan_info['name'], email_val)
                                
                                if link_data:
                                    # Handle User Creation ONLY if Guest
                                    is_shadow = False
                                    if not curr_u:
                                         # Check exist
                                         exist_user = db.query(AppUser).filter(AppUser.email == email_val).first()
                                         if exist_user:
                                             if exist_user.subscription_plan in ['STARTER', 'PRO', 'PRO_PLUS']:
                                                 st.warning("Account exists. Please Login.")
                                                 return
                                             # Recover existing pending user
                                             target_user = exist_user
                                         else:
                                             # Create Shadow
                                             temp_pass = str(uuid.uuid4())
                                             target_user = AppUser(
                                                 name="Valued Customer",
                                                 email=email_val, 
                                                 subscription_plan="AWAITING_PAYMENT", 
                                                 is_onboarded=False
                                             )
                                             target_user.set_password(temp_pass)
                                             db.add(target_user)
                                             db.commit()
                                             
                                             # Auto-Login Shadow
                                             st.session_state['user'] = target_user
                                             is_shadow = True
                                    
                                    # Set Payment State
                                    st.session_state['pending_payment'] = {
                                         "url": link_data.get('short_url'),
                                         "plan": plan_info['name'],
                                         "amount": final_price,
                                         "email": email_val,
                                         "is_shadow": is_shadow
                                    }
                                    if 'pending_signup_plan' in st.session_state:
                                         del st.session_state['pending_signup_plan']
                                    
                                    # REDIRECT
                                    st.success("Redirecting...")
                                    url = link_data.get('short_url')
                                    st.link_button("👉 Click to Pay", url, type="primary", use_container_width=True)
                                    import streamlit.components.v1 as components
                                    js = f"<script>window.open('{url}', '_blank'); window.parent.location.href = '{url}';</script>"
                                    components.html(js, height=0)
                                    return
                                else:
                                    st.error("Payment Gateway Error")
                            except Exception as e:
                                st.error(f"Error: {e}")
                        else:
                            st.warning("Email Required")

            signup_modal()
            
        else:
            # Fallback for old Streamlit
            st.warning("Your browser or app version does not support the Secure Signup Modal.")
            st.info("Please contact support at sandeepkashyap@hirelink.tech to upgrade manually.")

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
                    # HYDRATE QAs if missing for this user
                    if not is_admin:
                         current_count = db.query(QuestionAnswer).filter_by(user_id=user.id).count()
                         if current_count == 0:
                             # Seed standard questions for this user
                             # (Using a simplified list for now to ensure they have keys)
                             standard_qs = [
                                 ("What is your full name?", "personal"),
                                 ("What is your phone number?", "contact"),
                                 ("What is your current location?", "contact"),
                                 ("What is your LinkedIn URL?", "contact"),
                                 ("What are your top 3 skills?", "skills"),
                                 ("How many years of experience do you have?", "experience"),
                                 ("Are you willing to relocate?", "personal"),
                                 ("What is your notice period?", "personal"),
                                 ("What is your expected salary?", "personal"),
                                 ("Do you require visa sponsorship?", "legal")
                             ]
                             for q_text, cat in standard_qs:
                                 new_q = QuestionAnswer(user_id=user.id, question=q_text, category=cat, answer="")
                                 db.add(new_q)
                             db.commit() # Commit seeding
                    
                    # Fetch categories
                    if is_admin:
                        qa_list = db.query(QuestionAnswer).all()
                    else:
                        qa_list = db.query(QuestionAnswer).filter_by(user_id=user.id).all()
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
                 # SECURE FIX: Use the currently authenticated user, not the first in DB
                 if user:
                     # Re-fetch to attach to current DB session
                     user = db.merge(user)
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

# --- PASSWORD RESET FLOW (TOKEN HANDLER) ---
if st.query_params.get("reset_token"):
    reset_token = st.query_params.get("reset_token")
    # Validate
    from backend.database import SessionLocal, AppUser
    from datetime import datetime
    
    db_rst_chk = SessionLocal()
    u_rst_Target = db_rst_chk.query(AppUser).filter_by(reset_token=reset_token).first()
    
    if u_rst_Target and u_rst_Target.reset_token_expiry and u_rst_Target.reset_token_expiry > datetime.utcnow():
        # Valid Token found
        @st.dialog("🔐 Set New Password")
        def reset_pwd_modal():
            st.warning(f"Resetting password for: {u_rst_Target.email}")
            new_p = st.text_input("Enter New Password", type="password")
            confirm_p = st.text_input("Confirm Password", type="password")
            
            if st.button("Update Password", type="primary"):
                if new_p != confirm_p:
                    st.error("Passwords do not match.")
                elif len(new_p) < 4:
                    st.error("Too short.")
                else:
                    u_rst_Target.set_password(new_p)
                    u_rst_Target.reset_token = None # Invalidate token
                    u_rst_Target.reset_token_expiry = None
                    db_rst_chk.commit()
                    st.success("Password Updated! Redirecting to login...")
                    st.query_params.clear() # Prepare to clear
                    time.sleep(2)
                    st.rerun()
        
        reset_pwd_modal()
        
    else:
        st.error("Invalid or Expired Reset Link.")
        if st.button("Go Home"):
            st.query_params.clear()
            st.rerun()
            
    db_rst_chk.close()
    st.stop() # Stop normal rendering if in reset mode

from backend.utils.scraper_utils import run_scraper

# --- PAYMENT CALLBACK HANDLER ---
if "payment_success" in st.query_params:
    # URL: /?payment_success=true&razorpay_payment_id=...
    try:
        # Check if we were expecting a payment
        if 'pending_payment' in st.session_state:
             pp = st.session_state['pending_payment']
             
             # FORCE UPGRADE (Even if AWAITING_PAYMENT)
             update_user_plan(pp['plan'], pp.get('billing_cycle', 'MONTHLY')) 
             
             # Force Onboarding Start
             if 'user' in st.session_state:
                 st.session_state['show_onboarding'] = True
                 st.session_state['onboarding_step'] = 1
             
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
# --- MAIN CONTROLLER ---
try:
    # Check for Impersonation (God Mode) - Only if Admin already authenticated
    # BUT for now, let's just respect the 'user_id' stored in session
    # session_state['user'] contains the Object.
    
    # We rely on st.session_state['user'] set by Login logic above.
    user = st.session_state.get('user', None)
    
    # Additional Check: If object is detached/stale, re-fetch?
    if user:
         # Minimal validation
         pass
         
    # Impersonation Override (Only if an admin set it)
    impersonate_id = st.session_state.get('impersonating_user_id')
    if impersonate_id:
        # Check if current real user is admin?
        # Assuming the 'impersonating_user_id' was set by a secured admin action
        imp_user = db.query(backend.database.AppUser).get(impersonate_id)
        if imp_user:
             user = imp_user
             
except:
    user = None # Default to None (Logged Out) on error

if not user or st.session_state.get('force_landing', True):
    if st.session_state.get('show_login', False):
         # --- UNIFIED AUTH CENTER ---
         _, lc, _ = st.columns([1, 2, 1])
         with lc:
             # TOGGLE: Login vs Register
             default_idx = 1 if st.session_state.get('auth_mode_default') == "Create Account" else 0
             mode = st.radio(
                 "Auth Mode", 
                 ["Login", "Create Account"], 
                 horizontal=True, 
                 label_visibility="collapsed", 
                 key="auth_mode_widget",
                 index=default_idx
             )
             
             if mode == "Login":
                 st.markdown("## Login (v2.3)")
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
                                st.success("Success! Admin reset to 'admin@hirelink.com' / 'admin123'.")
                                st.warning("Please reload the page and login with these credentials.")
                                st.stop()
                            except Exception as e:
                                st.error(f"Reset Failed: {e}")
                                st.stop()
    
                        # SCOPED SESSION FOR ROBUST LOGIN
                        from backend.database import SessionLocal, AppUser
                        db_login = SessionLocal()
                        try:
                            u = db_login.query(AppUser).filter_by(email=email).first()
                            
                            if u and u.check_password(password):
                                db_login.expunge(u) 
                                st.session_state['user'] = u
                                st.session_state['force_landing'] = False
                                st.session_state['show_login'] = False
                                
                                # LOG ACTIVITY
                                try:
                                    from backend.database import ActivityLog
                                    db_login.add(ActivityLog(user_id=u.id, action="Login Success", details="Web Login"))
                                    db_login.commit()
                                except: pass
                                
                                st.success(f"Welcome back, {u.name}!")
                                
                                # CHECK PENDING PAYMENT (If they clicked "Choose Plan" then logged in)
                                if 'pending_signup_plan' in st.session_state:
                                    plan = st.session_state['pending_signup_plan']
                                    # Generate Link
                                    try:
                                        from backend.utils.payment_gateway import PaymentGateway
                                        pg_local = PaymentGateway()
                                        link = pg_local.create_payment_link(plan['amount'], plan['name'], u.email)
                                        if link:
                                            st.session_state['pending_payment'] = {'url': link.get('short_url'), 'plan': plan['name'], 'amount': plan['amount']}
                                            st.toast("Payment Link Ready! 💳")
                                    except Exception as e:
                                        st.error(f"Payment Init Error: {e}")

                                st.rerun()
                            else:
                                st.error("Invalid Email or Password")
                        except Exception as e:
                            st.error(f"Login Error: {e}")
                        finally:
                            db_login.close()
                 
                 if st.button("Forgot Password?", type="secondary"):
                     st.session_state['show_reset'] = True
                     st.session_state['show_login'] = False
                     st.rerun()
    
                 # Google Login Removed (Not Configured)
                 # st.markdown('<div style="text-align: center; margin: 15px 0; color: #64748b;">OR</div>', unsafe_allow_html=True)
                 # if st.button("🌐 Continue with Gmail", use_container_width=True):
                 #    pass

             else:
                 # --- REGISTER FORM ---
                 st.markdown("## Create Account")
                 
                 # Show plan intent if exists
                 if 'pending_signup_plan' in st.session_state:
                     p = st.session_state['pending_signup_plan']
                     st.info(f"✨ Creating account for **{p['name']}** Plan")

                 with st.form("register_form"):
                     new_name = st.text_input("Full Name")
                     new_email = st.text_input("Email Address")
                     new_pass = st.text_input("Create Password", type="password")
                     
                     reg_submit = st.form_submit_button("Create Account", type="primary", use_container_width=True)
                     
                     if reg_submit:
                         if new_name and new_email and new_pass:
                             from backend.database import SessionLocal, AppUser
                             db_reg = SessionLocal()
                             try:
                                 if db_reg.query(AppUser).filter_by(email=new_email).first():
                                     st.error("Email already exists. Please Login.")
                                 else:
                                     # Create
                                     nu = AppUser(name=new_name, email=new_email, subscription_plan="FREE", is_onboarded=False)
                                     nu.set_password(new_pass)
                                     db_reg.add(nu)
                                     db_reg.commit()
                                     db_reg.refresh(nu)
                                     db_reg.expunge(nu)
                                     
                                     # Login
                                     st.session_state['user'] = nu
                                     st.session_state['force_landing'] = False
                                     st.session_state['show_login'] = False
                                     
                                     # Handle Pending Plan
                                     if 'pending_signup_plan' in st.session_state:
                                        plan = st.session_state['pending_signup_plan']
                                        from backend.utils.payment_gateway import PaymentGateway
                                        pg_local = PaymentGateway()
                                        link = pg_local.create_payment_link(plan['amount'], plan['name'], nu.email)
                                        if link:
                                            st.session_state['pending_payment'] = {'url': link.get('short_url'), 'plan': plan['name'], 'amount': plan['amount']}
                                            st.toast("Account Created! Payment Link Ready 💳")
                                     else:
                                         st.success("Welcome! Let's set up your profile.")
                                     
                                     st.rerun()
                             except Exception as e:
                                 st.error(f"Registration Error: {e}")
                             finally:
                                 db_reg.close()
                         else:
                             st.warning("All fields are required.")

             if st.button("Back", use_container_width=True):
                 del st.session_state['show_login']
                 if 'pending_signup_plan' in st.session_state:
                     del st.session_state['pending_signup_plan']
                 st.rerun()

    elif st.session_state.get('show_reset', False):
        st.markdown("## 🔐 Reset Password")
        st.info("Enter your email to receive a secure reset link.")
        
        with st.form("reset_request_form"):
            rst_email = st.text_input("Email Address")
            if st.form_submit_button("Send Reset Link", type="primary", use_container_width=True):
                 # LOGIC
                 if rst_email:
                     from backend.database import SessionLocal, AppUser
                     from datetime import datetime, timedelta
                     import uuid
                     from backend.utils.notifier import EmailNotifier
                     
                     db_rst = SessionLocal()
                     try:
                         u_rst = db_rst.query(AppUser).filter_by(email=rst_email).first()
                         if u_rst:
                             token = str(uuid.uuid4())
                             u_rst.reset_token = token
                             u_rst.reset_token_expiry = datetime.utcnow() + timedelta(minutes=15)
                             db_rst.commit()
                             
                             base_url = "https://hirelink.tech" if "hirelink.tech" in str(st.query_params) else "http://localhost:8501"
                             link = f"{base_url}/?reset_token={token}"
                             
                             notifier = EmailNotifier()
                             if notifier.enabled:
                                 notifier.send_password_reset(rst_email, link)
                                 st.success("Link Sent! Check your email.")
                             else:
                                 st.warning("Email system disabled. Contact Admin.")
                                 st.info(f"Dev Link: {link}")
                         else:
                             st.error("Email not found.")
                     except Exception as e:
                         st.error(str(e))
                     finally:
                         db_rst.close()
            
        if st.button("Back to Login"):
            del st.session_state['show_reset']
            st.session_state['show_login'] = True # Restore Login view
            st.rerun()

    # EMERGENCY RECOVERY: Hidden Query Param to Fix Admin
    # URL: /?sys_admin_reset=true
    if st.query_params.get("sys_admin_reset") == "true":
        try:
            from backend.database import seed_admin
            seed_admin()
            st.success("SYSTEM RESET: Admin restored to admin@hirelink.com / admin123")
        except Exception as e:
            st.error(f"Reset Failed: {e}")
             
    elif st.session_state.get('show_onboarding', False):
        render_onboarding()
    else:
        render_landing_page(user_exists=(user is not None))
        check_and_show_payment_modal() # Ensure modal triggers on landing page too
else:
    check_and_show_signup_modal()
    check_and_show_payment_modal()

    # Sidebar
    st.sidebar.header("Navigation")

    # Sidebar
    st.sidebar.header("Navigation")
    is_admin = getattr(user, 'is_admin', False)
    st.sidebar.markdown(f"**👤 {user.name}**{' (Admin)' if is_admin else ''}")
    
    # LOGOUT
    if st.sidebar.button("Log Out"):
         # Log Activity
         try:
             from backend.database import SessionLocal, ActivityLog
             db_log = SessionLocal()
             db_log.add(ActivityLog(user_id=user.id, action="Logout", details="User initiated logout"))
             db_log.commit()
             db_log.close()
         except: pass

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

    # ADMIN TOOLS
    if getattr(user, 'is_admin', False):
        with st.sidebar.expander("⚙️ Admin Settings"):
            st.caption("Configure System")
            
            # GEMINI KEY SETTER
            # Security: Check existence without exposing value
            sb_key_exists = bool(os.getenv("GEMINI_API_KEY"))
            if not sb_key_exists:
                 # Check DB if not in env
                 from backend.database import SessionLocal, PortalCredential
                 db_cred = SessionLocal()
                 existing = db_cred.query(PortalCredential).filter_by(portal_name="GEMINI_API_KEY").first()
                 if existing:
                     sb_key_exists = True
                 db_cred.close()
            
            sb_placeholder = "********" if sb_key_exists else ""
            
            # FIXED: Do not put secret in 'value'
            new_key = st.text_input(
                "Gemini API Key", 
                value="", 
                placeholder=sb_placeholder, 
                type="password",
                key="sb_admin_settings_key" 
            )
            if st.button("Save Key"):
                if new_key and new_key != "********":
                    from backend.database import SessionLocal, PortalCredential
                    db_cred = SessionLocal()
                    try:
                        cred = db_cred.query(PortalCredential).filter_by(portal_name="GEMINI_API_KEY").first()
                        if not cred:
                            cred = PortalCredential(portal_name="GEMINI_API_KEY", username="apikey", user_id=user.id)
                            db_cred.add(cred)
                        cred.password = new_key # Storing plain for MVP as per spec
                        db_cred.commit()
                        st.success("API Key Saved! Reloading...")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Save Failed: {e}")
                    finally:
                        db_cred.close()


    # PLAN USAGE METER
    st.sidebar.markdown("---")
    
    # RE-FETCH USER FROM DB TO ENSURE FRESHNESS (e.g. after Admin Upgrade)
    # This fixes the issue of "stale session state" showing old plan
    try:
        from backend.database import SessionLocal, AppUser, Application
        db_usage = SessionLocal()
        fresh_user = db_usage.query(AppUser).filter_by(id=user.id).first()
        if fresh_user:
            plan = fresh_user.subscription_plan or 'FREE'
            is_admin_check = fresh_user.is_admin
        else:
            plan = getattr(user, 'subscription_plan', 'FREE')
            is_admin_check = getattr(user, 'is_admin', False)
            
        if is_admin_check:
            limit = 999999
            plan_display = f"{plan} (ADMIN)"
        else:
            limit_map = {'TRIAL': 20, 'FREE': 20, 'STARTER': 150, 'PRO': 1000, 'PRO_PLUS': 10000}
            limit = limit_map.get(plan, 20)
            plan_display = plan

        # Count apps (FILTERED BY USER)
        apps_used = db_usage.query(Application).filter_by(user_id=user.id).count()
        db_usage.close()
    except Exception as e:
        logger.error(f"Usage check failed: {e}")
        apps_used = 0
        limit = 20
        plan_display = "Error"
        
    st.sidebar.caption(f"**PLAN:** {plan_display}")
    if limit < 999999 and limit > 0:
        st.sidebar.progress(min(apps_used / limit, 1.0))
    
    st.sidebar.divider()
    st.sidebar.caption("HireLink v2.5 (Admin V2)")
        
    st.sidebar.caption(f"{apps_used} / {'∞' if limit > 900000 else limit} Applications Used")
    
    # --- PENDING PAYMENT ALERT ---
    if 'pending_payment' in st.session_state:
        pp = st.session_state['pending_payment']
        st.sidebar.warning("⚠️ **Payment Pending**")
        st.sidebar.markdown(f"finish upgrading to **{pp['plan']}**")
        st.sidebar.link_button("👉 Complete Payment", pp['url'], use_container_width=True)
        if st.sidebar.button("Cancel", key="cancel_pay_sidebar"):
            del st.session_state['pending_payment']
            st.rerun()
        st.sidebar.divider()

    
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
    
    nav_options = ["🏠 Dashboard", "👤 Pilot Profile", "🚀 Job Pilot", "💳 Subscription", "🤝 Affiliate Program"]
    if is_admin:
        nav_options.append("🛡️ Admin Console")
        
    menu = st.sidebar.radio("Go to", nav_options)

    # ... (Other menus same) ...
    
    if menu == "💳 Subscription":
        render_pricing_logic(user_exists=True)

    if menu == "🛡️ Admin Console":
        # SECURITY CHECK
        if not is_admin: # Double check
            st.error("Access Denied.")
            st.stop()
            
        st.header("🛡️ Admin Console")
        st.markdown("Manage users and system health.")
        
        tab_dash, tab_users, tab_market, tab_activity, tab_snapshots, tab_export = st.tabs(["📊 Dashboard", "👥 User Management", "🎟️ Marketing", "📜 Activity Logs", "💾 Snapshots", "📤 Data Export"])
        
        # --- TAB 4: DATA EXPORT ---
        with tab_export:
            st.subheader("💾 System Data Export")
            st.markdown("Download full system data for backup or analysis.")
            
            c_ex1, c_ex2 = st.columns([2, 1])
            with c_ex1:
                st.info("ℹ️ Exports include: Users, Smart Answers, and Application History.")
            
            with c_ex2:
                # Helper to generating Excel
                def get_excel_export():
                    import io
                    try:
                        buffer = io.BytesIO()
                        # specific engine to ensure compatibility
                        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                            # 1. Users
                            users_df = pd.read_sql(db.query(backend.database.AppUser).statement, db.bind)
                            # Remove sensitive hash if present
                            if 'password' in users_df.columns: del users_df['password']
                            users_df.to_excel(writer, sheet_name='Users', index=False)
                            
                            # 2. QAs
                            qa_df = pd.read_sql(db.query(QuestionAnswer).statement, db.bind)
                            qa_df.to_excel(writer, sheet_name='Smart_Answers', index=False)
                            
                            # 3. Applications
                            app_df = pd.read_sql(db.query(Application).statement, db.bind)
                            app_df.to_excel(writer, sheet_name='Applications', index=False)
                            
                        return buffer.getvalue()
                    except ImportError:
                        st.error("Missing 'openpyxl'. Please install it to export Excel.")
                        return None
                    except Exception as e:
                        st.error(f"Export Failed: {e}")
                        return None

                # Generate on click (or prepared)
                # Since we can't generate inside the button callback easily for download_button, 
                # we usually generate it on page load OR uses a callback to set state.
                # However, for admin, generating on render is acceptable for small DBs.
                # For larger DBs, we'd use a "Prepare Export" button.
                
                if st.button("Prepare Export File"):
                    data = get_excel_export()
                    if data:
                        st.session_state['export_data'] = data
                        st.success("Export Ready!")
                
                if 'export_data' in st.session_state:
                     st.download_button(
                         label="⬇️ Download Backup (.xlsx)",
                         data=st.session_state['export_data'],
                         file_name=f"hirelink_backup_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                         mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                         type="primary"
                     )

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
            c_chart1, c_chart2 = st.columns(2)
            
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
            if is_admin:
                recent_apps = db.query(Application, Job).join(Job, Application.job_id == Job.id).order_by(Application.applied_at.desc()).limit(50).all()
            else:
                # JOIN Application -> Resume to ensure ownership if user_id missing, OR check user_id
                # Simplest check: Filter by Resume Email that matches User Email
                recent_apps = db.query(Application, Job).join(Job, Application.job_id == Job.id)\
                            .join(Resume, Application.resume_id == Resume.id)\
                            .filter(Resume.email == user.email)\
                            .order_by(Application.applied_at.desc()).limit(20).all()
            
            if recent_apps:
                app_data = []
                for app, job in recent_apps:
                    # Fix: Handle NoneType for match_score
                    score_display = f"{app.match_score:.2f}" if app.match_score is not None else "N/A"
                    
                    app_data.append({
                        "Date": app.applied_at.strftime("%Y-%m-%d %H:%M"),
                        "Role": job.title,
                        "Company": job.company,
                        "Portal": job.source,
                        "Status": app.status,
                        "Score": score_display
                    })
                st.dataframe(pd.DataFrame(app_data), use_container_width=True)
            else:
                st.info("No applications sent yet.")

            st.markdown("---")
            # --- SYSTEM CONFIGURATION ---
            st.subheader("⚙️ System Configuration")
            # Security: Never send the raw key to the client. Use a placeholder.
            current_key_exists = bool(os.getenv("GEMINI_API_KEY"))
            
            with st.form("config_form"):
                st.markdown("**LLM Settings (Gemini)**")
                st.caption("Required for Smart Resume Parsing and Cover Letters.")
                
                # If key exists, show placeholder. If not, show empty.
                placeholder_text = "********" if current_key_exists else ""
                
                # NOTE: We do NOT populate 'value' with the secret logic.
                new_key = st.text_input("Gemini API Key", value="", type="password", placeholder=placeholder_text, help="Enter a new key to update. Leave blank to keep existing.")
                
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
                                st.error("Cannot delete yourself.")
                            else:
                                db.delete(u)
                                db.commit()
                                st.success("User Deleted.")
                                del st.session_state[del_key]
                                st.rerun()
                        
                        if col_cancel.button("Cancel", key=f"conf_no_{u.id}"):
                            del st.session_state[del_key]
                            st.rerun()
                            
                    else:
                        c_act1, c_act2, c_act3 = st.columns(3) # Added a third column for the new button
                        # Impersonate Button
                        if c_act1.button("👁️ Login As", key=f"imp_{u.id}"):
                             st.session_state['impersonating_user_id'] = u.id
                             st.session_state['force_landing'] = False # Ensure we don't get stuck on landing
                             st.rerun()
                        
                        # Delete Button
                        if c_act2.button("🗑️ Delete", key=f"del_{u.id}"):
                            st.session_state[del_key] = True
                            st.rerun()
                            

        
        # --- TAB: MARKETING & CAMPAIGNS ---
        with tab_market:
            st.subheader("📢 Marketing Automation Center")
            
            mk_tab1, mk_tab2 = st.tabs(["🚀 Campaign Manager", "🎟️ Coupons & Offers"])
            
            with mk_tab1:
                st.info("💡 **Drip Campaigns:** Automated emails sent to Free users based on account age.")
                
                from backend.marketing_engine import MarketingEngine
                from backend.database import MarketingCampaign
                engine_mk = MarketingEngine()
                
                # Stats
                stats = engine_mk.get_campaign_status()
                m1, m2 = st.columns(2)
                m1.metric("Active Campaigns", stats['active_campaigns'])
                m2.metric("Total Emails Sent", stats['emails_delivered'])
                
                st.divider()
                
                # Campaign Editor
                st.markdown("#### 📝 Edit Campaigns")
                campaigns = db.query(MarketingCampaign).order_by(MarketingCampaign.day_offset).all()
                
                for camp in campaigns:
                    with st.expander(f"Day {camp.day_offset}: {camp.name}", expanded=False):
                        with st.form(f"edit_camp_{camp.id}"):
                            new_subj = st.text_input("Subject", value=camp.subject)
                            new_body = st.text_area("HTML Body", value=camp.body_template, height=150)
                            
                            c_save, c_preview = st.columns([1, 1])
                            if c_save.form_submit_button("Save Changes", type="primary"):
                                camp.subject = new_subj
                                camp.body_template = new_body
                                db.commit()
                                st.success("Saved!")
                                st.rerun()
                                
                            # Basic Preview
                            st.caption("Preview:")
                            st.markdown(new_body, unsafe_allow_html=True)

                st.divider()
                
                # Execution Control
                st.markdown("#### ⚡ Operations")
                c_run, c_log = st.columns([1, 2])
                with c_run:
                    st.caption("Process the email queue for today.")
                    if st.button("🚀 Run Daily Campaign Now", type="primary"):
                        with st.spinner("Sending emails..."):
                            logs = engine_mk.run_daily_campaign(dry_run=False)
                            st.session_state['mk_logs'] = logs
                            if logs:
                                st.success("Campaign Run Complete!")
                            else:
                                st.info("No eligible users found for today.")
                                
                with c_log:
                    if 'mk_logs' in st.session_state:
                        with st.status("Execution Log", expanded=True):
                            for l in st.session_state['mk_logs']:
                                st.write(l)

            with mk_tab2:
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


        # --- TAB: ACTIVITY LOGS ---
        with tab_activity:
            st.subheader("📜 User Activity Feed")
            st.caption("Live monitoring of user actions (Logins, Applications, Updates)")
            
            # Filters
            act_c1, act_c2, act_c3 = st.columns([3, 1, 1])
            with act_c1:
                # Fetch Users for Dropdown
                all_users_act = db.query(backend.database.AppUser).all()
                user_opts = ["All Users"] + [f"{u.email} : {u.id}" for u in all_users_act]
                sel_user_filter = st.selectbox("Filter User", user_opts)
                
            with act_c2:
                limit = st.selectbox("Limit", [50, 100, 200, 500], index=1)
            with act_c3:
                st.write("") # Align
                if st.button("🔄 Refresh Feed", use_container_width=True):
                    st.rerun()
                
            from backend.database import ActivityLog
            query = db.query(ActivityLog, backend.database.AppUser).join(backend.database.AppUser, ActivityLog.user_id == backend.database.AppUser.id).order_by(ActivityLog.timestamp.desc())
            
            if sel_user_filter != "All Users":
                # Extract ID from "email : id" string
                target_id = int(sel_user_filter.split(" : ")[-1])
                query = query.filter(ActivityLog.user_id == target_id)
            
            logs = query.limit(limit).all()
            
            if logs:
                log_data = []
                for log, u in logs:
                    # Emoji mapping
                    icon = "🔹"
                    if "Login" in log.action: icon = "🟢"
                    elif "Logout" in log.action: icon = "⚪"
                    elif "Mission" in log.action: icon = "🚀"
                    elif "Application" in log.action: icon = "✅"
                    elif "Failed" in log.action: icon = "❌"
                    elif "Profile" in log.action: icon = "✏️"
                    
                    log_data.append({
                        "Time": log.timestamp,
                        "User": f"{u.name}",
                        "Email": u.email,
                        "Action": f"{icon} {log.action}",
                        "RawAction": log.action, # For charts
                        "Details": log.details
                    })
                
                df_logs = pd.DataFrame(log_data)
                
                # --- ANALYTICS DASHBOARD ---
                st.markdown("#### 📊 Insights")
                c_chart1, c_chart2 = st.columns([2, 1])
                
                with c_chart1:
                    # Activity over Time
                    st.caption("Activity Volume (Last 24h)")
                    if not df_logs.empty:
                        df_chart = df_logs.set_index("Time")
                        st.bar_chart(df_chart["RawAction"].resample("H").count(), color="#6366f1")
                        
                with c_chart2:
                    # Action Distribution
                    st.caption("Action Types")
                    if not df_logs.empty:
                        action_counts = df_logs["RawAction"].value_counts()
                        st.dataframe(action_counts, use_container_width=True)

                st.divider()

                # Interactive Table
                c_tbl, c_dl = st.columns([4, 1])
                with c_tbl:
                    st.markdown("#### 📝 Detailed Log")
                with c_dl:
                     # CSV Download
                     csv = df_logs.to_csv(index=False).encode('utf-8')
                     st.download_button(
                         "⬇️ Export CSV",
                         csv,
                         "activity_logs.csv",
                         "text/csv",
                         key='download-csv'
                     )

                st.data_editor(
                    df_logs[["Time", "User", "Email", "Action", "Details"]],
                    use_container_width=True,
                    disabled=True,
                    hide_index=True,
                    column_config={
                        "Time": st.column_config.DatetimeColumn("Timestamp", format="D MMM, HH:mm:ss"),
                        "Action": st.column_config.TextColumn("Event Type"),
                    }
                )
            else:
                st.info("No activity logs found yet. Users need to verify login or start missions.")
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
        # Metric Calculations (USER ISOLATED)
        session = get_db_session()
        # We only count jobs relevant to the user? No, Scraped jobs are global (Market Data).
        # WAITING: User might want 'My Jobs'. But "Total Scraped" usually implies system availability.
        # BUT 'Talent Profiles' and 'Applications' MUST be private.
        
        # 1. Total Scraped (Global Market View - OK to keep global or filter by user's search?)
        # Let's keep Total Scraped Global as it represents "Platform Power".
        total_jobs = session.query(backend.database.Job).count() 
        
        # 2. Resumes (PRIVATE - Linked by Email)
        # Fix: Resume table lacks user_id, use email mapping
        total_resumes = session.query(backend.database.Resume).filter(backend.database.Resume.email == user.email).count()
        
        # 3. Applications (PRIVATE)
        try:
             # Application table HAS user_id
             total_apps = session.query(backend.database.Application).filter(backend.database.Application.user_id == user.id).count()
        except:
             total_apps = 0
             
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
            if is_admin:
                all_apps = db.query(Application, Job).join(Job, Application.job_id == Job.id).order_by(Application.applied_at.desc()).all()
            else:
                all_apps = db.query(Application, Job).join(Job, Application.job_id == Job.id)\
                            .join(Resume, Application.resume_id == Resume.id)\
                            .filter(Resume.email == user.email)\
                            .order_by(Application.applied_at.desc()).all()
            
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
            
            # --- PAUSE / RESUME CONTROL ---
            pause_lock_file = os.path.join(os.getcwd(), "data", "bot_pause.lock")
            is_paused = os.path.exists(pause_lock_file)
            
            c_eng, c_pause = st.columns([3, 1])
            
            with c_eng:
                # --- GUARD: CREDENTIAL CHECK ---
                has_creds = False
                with SessionLocal() as db_check:
                    if db_check.query(PortalCredential).filter(PortalCredential.user_id == user.id).first():
                        has_creds = True
                
                if has_creds:
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
                else:
                    st.warning("⚠️ Setup Required: Missing Credentials")
                    with st.expander("🔑 Quick Add Credentials", expanded=True):
                        st.caption("You must configure at least one portal to fly.")
                        qa_portal = st.selectbox("Select Portal", ["LinkedIn", "Naukri", "Indeed"])
                        qa_user = st.text_input("Username/Email", key="qa_u")
                        qa_pass = st.text_input("Password", type="password", key="qa_p")
                        
                        if st.button("Save & Unlock", type="primary"):
                            if qa_user and qa_pass:
                                try:
                                    with SessionLocal() as db_q:
                                        # Update or Insert
                                        existing_c = db_q.query(PortalCredential).filter_by(user_id=user.id, portal_name=qa_portal).first()
                                        if existing_c:
                                            existing_c.username = qa_user
                                            existing_c.password = qa_pass
                                        else:
                                            new_c = PortalCredential(user_id=user.id, portal_name=qa_portal, username=qa_user, password=qa_pass)
                                            db_q.add(new_c)
                                        db_q.commit()
                                    st.success("Saved! Reloading...")
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")
                            else:
                                st.error("Please enter both username and password.")
            
            with c_pause:
                if is_paused:
                    if st.button("▶️ RESUME", type="primary", use_container_width=True, help="Resume the Autopilot"):
                        if os.path.exists(pause_lock_file): os.remove(pause_lock_file)
                        st.rerun()
                else:
                    if st.button("⏸️ PAUSE", type="secondary", use_container_width=True, help="Pause the Autopilot safely"):
                        os.makedirs(os.path.dirname(pause_lock_file), exist_ok=True)
                        with open(pause_lock_file, "w") as f: f.write("paused")
                        st.rerun()
            
            if is_paused:
                st.warning("⚠️ Autopilot is PAUSED. Click RESUME to continue operations.")

        # Space between Mission Control and Systems Log
        for _ in range(3): st.write("")

        # Terminal
        log_expander = st.expander("🛠️ Internal Systems Briefing", expanded=False)
        log_terminal = log_expander.empty()

        # --- RUN AUTOMATION (If triggered) ---
        # --- RUN AUTOMATION (If triggered) ---
        if st.session_state.get('pilot_running', False):
            from backend.automation_runner import run_pilot_mission
            run_pilot_mission(
                role, loc, sel_res_id, sel_portals, user.email, 
                render_phases, update_stats_ui, log_terminal
            )

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
        # 1. THE HOOK
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); padding: 30px; border-radius: 20px; color: white; margin-bottom: 20px; box-shadow: 0 10px 30px -5px rgba(79, 70, 229, 0.4);">
            <h2 style="color: white; margin:0;">Give 20%, Get ₹500 ✨</h2>
            <p style="font-size: 1.1rem; opacity: 0.9; margin-top: 10px;">Invite your friends to HireLink. They get <b>20% OFF</b> their first plan, and you get <b>₹500 Credit</b> applied to your next renewal.</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.caption("👇 Copy your unique referral link:")
        st.code(f"https://www.hirelink.tech/?ref={user.referral_code}", language="text")

        st.markdown("---")

        # 2. STATS DASHBOARD
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("💰 Rewards Overview")
        # Calculate Stats Logic (Force Reload 1)
        active_refs = db.query(backend.database.AppUser).filter(backend.database.AppUser.referred_by_id == user.id, backend.database.AppUser.subscription_plan != "TRIAL").count()
        total_credits = db.query(func.sum(backend.database.ReferralTransaction.amount)).filter(backend.database.ReferralTransaction.referrer_id == user.id).scalar() or 0

        # Render Widgets
        st.markdown(f"""
        <div style="display: flex; gap: 15px; margin-bottom: 20px;">
            <div style="flex: 1; background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 20px 10px; text-align: center;">
                <div style="font-size: 0.7rem; color: #94a3b8; text-transform: uppercase; font-weight: 600;">Friends Reached</div>
                <div style="font-size: 1.8rem; font-weight: 800; color: white;">{user.referral_count}</div>
                <div style="color: #4ade80; font-size: 0.8rem; margin-top: 5px;">Total</div>
            </div>
            <div style="flex: 1; background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 20px 10px; text-align: center;">
                <div style="font-size: 0.7rem; color: #94a3b8; text-transform: uppercase; font-weight: 600;">Active Referrals</div>
                <div style="font-size: 1.8rem; font-weight: 800; color: white;">{active_refs}</div>
                <div style="color: #4ade80; font-size: 0.8rem; margin-top: 5px;">Paying</div>
            </div>
            <div style="flex: 1; background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 20px 10px; text-align: center;">
                <div style="font-size: 0.7rem; color: #94a3b8; text-transform: uppercase; font-weight: 600;">Service Credits</div>
                <div style="font-size: 1.8rem; font-weight: 800; color: white;">₹{round(total_credits, 2)}</div>
                <div style="color: #4ade80; font-size: 0.8rem; margin-top: 5px;">Lifetime Earned</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

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
            # Filter resumes by the current user's email
            resumes = db.query(Resume).filter(Resume.email == user.email).all()
            
            if not resumes:
                st.info("No resumes found. Upload one above!")
            
            for r in resumes:
                with st.container():
                    st.markdown(f"""
                    <div style="background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 20px; margin-bottom: 15px;">
                        <div style="display: flex; justify-content: space-between; align-items: start;">
                            <div>
                                <h4 style="margin: 0; color: white;">{r.name or 'Unknown Candidate'}</h4>
                                <p style="margin: 5px 0 0 0; color: #94a3b8; font-size: 0.9rem;">{r.email} • {r.phone or 'No Phone'}</p>
                            </div>
                            <div style="text-align: right;">
                                <span style="background: rgba(79, 70, 229, 0.2); color: #818cf8; padding: 4px 10px; border-radius: 12px; font-size: 0.8rem;">Parsed ID: {r.id}</span>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Collapsible Details
                    with st.expander("View Parsed Details"):
                        data = r.parsed_data or {}
                        
                        if data.get('skills'):
                            st.write("**🛠️ Skills**")
                            st.markdown(f"""
                            <div style="display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px;">
                                {''.join([f'<span style="background-color:#2b2d42; color:white; padding:4px 10px; border-radius:12px; font-size:0.85rem; border:1px solid rgba(255,255,255,0.1);">{s}</span>' for s in data.get('skills', [])])}
                            </div>
                            """, unsafe_allow_html=True)
                            
                        if data.get('experience'):
                            st.divider()
                            st.write("**💼 Experience**")
                            exp = data.get('experience')
                            if isinstance(exp, list):
                                for e in exp:
                                    st.caption(f"**{e.get('role', 'Role')}** at {e.get('company', 'Company')} ({e.get('years', '')})")
                            else:
                                st.write(str(exp))

                    # Actions
                    col_act_1, col_act_2 = st.columns([0.70, 0.30])
                    with col_act_2:
                         # Key for confirmation state
                         confirm_key = f"confirm_del_{r.id}"
                         
                         if st.session_state.get(confirm_key):
                             st.warning("Confirm?")
                             c_yes, c_no = st.columns(2)
                             if c_yes.button("Yes", key=f"yes_{r.id}"):
                                 confirm_delete_resume(r.id, r.name)
                                 # Reset state
                                 st.session_state[confirm_key] = False
                                 st.rerun()
                             if c_no.button("No", key=f"no_{r.id}"):
                                 st.session_state[confirm_key] = False
                                 st.rerun()
                         else:
                             if st.button("🗑️ Delete", key=f"del_{r.id}", type="secondary"):
                                 st.session_state[confirm_key] = True
                                 st.rerun()

        # --- TAB 2: SMART ANSWERS ---
        with tab_smart:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.subheader("Knowledge Base")
            st.markdown("This is the **brain** of your agent. The more questions you answer here, the accurately it can fill forms.")
            st.info("ℹ️ **Note**: You may encounter similar or duplicate questions. Please answer them all—redundancy helps the AI apply correctly to different portals.")
            
            # --- INSTANT SAVE PATTERN (No Form) ---
            # Fetch all questions
            # Always filter by current user to prevent data leakage, even for admins.
            # Admins can inspect others via the dedicated Admin Console if needed.
            qa_list = db.query(QuestionAnswer).filter_by(user_id=user.id).all()
            if not qa_list:
                with st.status("Initializing Knowledge Base...", expanded=True) as status:
                    from backend.database import seed_user_questions
                    success, msg = seed_user_questions(user.id)
                    if success:
                        status.update(label="Knowledge Base Ready!", state="complete", expanded=False)
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Failed to initialize: {msg}")
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
                # Sort based on priority map, defaulting to 100 for others (sorted alphabetically among themselves)
                categories = sorted(raw_categories, key=lambda x: (CATEGORY_PRIORITY.get((x or "").lower(), 100), (x or "")))
                
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

# --- FINAL MODAL CHECK ---
# Ensures payment dialog works regardless of page
check_and_show_payment_modal()

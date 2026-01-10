import streamlit as st
st.set_page_config(page_title="Hire Link", layout="wide", initial_sidebar_state="expanded")
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

from backend.database import init_db, get_db, Job, Resume, Application, PortalStatus, QuestionAnswer, Coupon, PortalCredential
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

# Load Custom CSS
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

try:
    local_css("assets/style.css")
except:
    pass # Fallback if file missing



db = next(get_db())

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

# --- LANDING PAGE ---
def render_landing_page(user_exists=False):
    # Top Navigation (Login)
    # --- HEADER SECTION ---
    # Aligns Logo (Left) and Login/Nav (Right)
    h_col1, h_col2 = st.columns([6, 1])
    
    with h_col1:
        st.image("assets/logo.png", width=220)
        
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

    st.markdown("""
    <div class="landing-container">
        <div class="landing-hero">
            <h1 class="landing-title">Automate Your <span class="gradient-text">Dream Job</span> Search today.</h1>
            <p class="landing-subtitle">Stop manually applying. Let our AI Agent find, filter, and apply to thousands of jobs for you while you sleep.</p>
            <div class="landing-trust">
                <span>⭐️⭐️⭐️⭐️⭐️ Trusted by 5,000+ Job Seekers</span>
                <span class="trust-badge">🔒 Secure & Private</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Centered CTA Buttons
    c1, c2, c3, c4 = st.columns([1, 2, 2, 1])
    with c2:
        # Check if we should show "Get Started" or "Dashboard"
        lbl = "Start Applying Now 🚀" if not user_exists else "Go to Dashboard 🚀"
        if st.button(lbl, type="primary", use_container_width=True):
            if user_exists:
                st.session_state['force_landing'] = False
            else:
                st.session_state['show_onboarding'] = True
            st.rerun()
            
    with c3:
        if st.button("Existing User Login", type="secondary", use_container_width=True):
             st.session_state['show_login'] = True
             st.rerun()

    st.markdown("""
    <div class="landing-features">
        <div class="feature-card">
            <div class="feature-icon">🔍</div>
            <h3>Smart Search</h3>
            <p>We scrape LinkedIn, Naukri, and Indeed deeply.</p>
        </div>
        <div class="feature-card">
            <div class="feature-icon">⚡️</div>
            <h3>Auto-Apply</h3>
            <p>One-click apply to hundreds of relevant roles.</p>
        </div>
        <div class="feature-card">
            <div class="feature-icon">🧠</div>
            <h3>AI Resume Match</h3>
            <p>We only apply if your resume score is >70%.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="landing-portals">
        <h2 style="text-align: center; margin-bottom: 40px; font-size: 2.5rem;">Supported <span class="gradient-text">Platforms</span> 🌐</h2>
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
    """, unsafe_allow_html=True)

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

def render_pricing(user_exists):
    # --- PAYMENT MODAL ---
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
                    coupon = db.query(backend.database.Coupon).filter(backend.database.Coupon.code == code_input).first()
                    if coupon:
                        # Apply Discount
                        if 'original_amount' not in pp:
                             pp['original_amount'] = pp['amount'] # Store base price
                             
                        base = pp['original_amount']
                        disc_amt = int(base * (1 - coupon.discount_percent/100))
                        
                        # Regenerate Link with new price
                        # Note: We need email here. 'user' object is outside scope, logic fix needed.
                        # Assuming user email is available or stored in pp if needed.
                        # Actually 'user' is available in render_pricing scope if we pass or query it.
                        # But wait, create_payment_link needs user email.
                        # Let's assume pp needs 'email' too.
                        
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
                
                # Record Coupon Usage if any
                if 'applied_coupon' in pp:
                     u = db.query(backend.database.AppUser).filter(backend.database.AppUser.email == pp['email']).first()
                     if u: 
                         u.used_coupon_code = pp['applied_coupon']
                         db.commit()
                         
                st.success("Payment Verified! Upgraded.")
                del st.session_state['pending_payment']
                st.rerun()
                
            if st.button("Cancel"):
                del st.session_state['pending_payment']
                st.rerun()

        pay_modal()

    st.markdown("""
    <div class="pricing-section">
        <h2 style="text-align: center; font-size: 2.5rem; margin-bottom: 10px;">Plans for Every Career Stage</h2>
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

    # Grid with padding
    _, c1, c2, c3, _ = st.columns([0.2, 3, 3, 3, 0.2])
    
    # --- FREE ---
    with c1:
        st.markdown(f"""
        <div class="pricing-card">
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
        if st.button("Start Free", key="btn_free", use_container_width=True):
             st.session_state['selected_plan'] = 'FREE'
             if not user_exists: st.session_state['show_onboarding'] = True
             else: update_user_plan('FREE') 
             st.rerun()

    # --- SIDEBAR FOOTER ---
    with st.sidebar:
        st.markdown("---")
        if st.button("🔴 Reset App State (Debug)", use_container_width=True):
             for key in list(st.session_state.keys()):
                 del st.session_state[key]
             st.rerun()

    # --- STARTER ---
    with c2:
        st.markdown(f"""
        <div class="pricing-card">
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
        if st.button("Choose Starter", key="btn_starter", use_container_width=True):
             if not user_exists:
                 st.session_state['selected_plan'] = 'STARTER'
                 st.session_state['show_onboarding'] = True
                 st.rerun()
             else:
                 # Payment Flow
                 link_data = pg.create_payment_link(p_starter, "STARTER", user.email)
                 if link_data:
                     st.session_state['pending_payment'] = {
                         "url": link_data.get('short_url'),
                         "plan": "STARTER",
                         "amount": p_starter,
                         "email": user.email
                     }
                     st.rerun()



    # --- PRO ---
    with c3:
        st.markdown(f"""
        <div class="pricing-card featured">
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
        if st.button("Choose Pro", key="btn_pro", type="primary", use_container_width=True):
             if not user_exists:
                 st.session_state['selected_plan'] = 'PRO'
                 st.session_state['show_onboarding'] = True
                 st.rerun()
             else:
                 # Payment Flow
                 link_data = pg.create_payment_link(p_pro, "PRO", user.email)
                 if link_data:
                     st.session_state['pending_payment'] = {
                         "url": link_data.get('short_url'),
                         "plan": "PRO",
                         "amount": p_pro,
                         "email": user.email
                     }
                     st.rerun()

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
                loc = st.text_input("CURRENT LOCATION *", placeholder="e.g. New York, USA")
                linkedin = st.text_input("LINKEDIN PROFILE *", placeholder="https://www.linkedin.com/in/username")
                website = st.text_input("PERSONAL WEBSITE", placeholder="https://yourportfolio.com")
                github = st.text_input("GITHUB PROFILE", placeholder="https://github.com/username")
                
                st.write("")
                if st.form_submit_button("NEXT STEP", type="primary", use_container_width=True):
                    if name and email and loc and linkedin:
                        # Save to Session State Temp
                        st.session_state['ob_name'] = name
                        st.session_state['ob_email'] = email
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
                    is_first_user = db.query(backend.database.AppUser).count() == 0
                    
                    user = backend.database.AppUser(
                        name=st.session_state.get('ob_name'),
                        email=st.session_state.get('ob_email'),
                        curr_loc=st.session_state.get('ob_loc'),
                        linkedin=st.session_state.get('ob_linkedin'),
                        website=st.session_state.get('ob_website'),
                        github=st.session_state.get('ob_github'),
                        target_roles=st.session_state.get('ob_roles'),
                        target_cities=st.session_state.get('ob_cities'),
                        skip_companies=st.session_state.get('ob_skip'),
                        work_mode=work_mode,
                        instructions=instructions,
                        is_onboarded=False,
                        is_admin=is_first_user, # Grant Admin to first user
                        subscription_plan=st.session_state.get('selected_plan', 'TRIAL')
                    )
                    db.add(user)
                    db.commit()

                    # --- APPLY REFERRAL ---
                    if st.session_state.get('captured_ref'):
                        from backend.utils.affiliate_manager import AffiliateManager
                        AffiliateManager.apply_referral(user.id, st.session_state['captured_ref'])

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
             email = st.text_input("Email")
             password = st.text_input("Password", type="password")
             
             c_btn1, c_btn2 = st.columns([1, 1])
             with c_btn1:
                 if st.button("Sign In", type="primary", use_container_width=True):
                     from backend.database import AppUser
                     u = db.query(AppUser).filter_by(email=email).first()
                     if u and u.password == password: 
                         st.session_state['force_landing'] = False
                         st.session_state['show_login'] = False
                         st.success(f"Welcome back, {u.name}!")
                         time.sleep(1)
                         st.rerun()
                     else:
                         st.error("Invalid credentials.")
             
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
        
        tab_dash, tab_users, tab_market = st.tabs(["📊 Dashboard", "👥 User Management", "🎟️ Marketing"])
        
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



# ... (Rest of app) ...

    if menu == "🏠 Dashboard":
        # HERO SECTION
        st.markdown(f"""
        <div style="padding: 2rem 0; margin-bottom: 2rem; border-bottom: 1px solid rgba(255,255,255,0.1);">
            <h1 style="margin:0; font-size: 3rem;">Hello, {user.name.split()[0]} 👋</h1>
            <p style="color: #94a3b8; font-size: 1.2rem; margin-top: 10px;">
                Your AI Recruiter is active. Here is your mission status.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        if tour_mode:
            st.info("💡 **Dashboard:** This is your command center. See scraped jobs, active resumes, and application history.")
        
        # 1. METRICS (Auto-styled by CSS)
        col1, col2, col3 = st.columns(3)
        total_jobs = db.query(Job).count()
        total_resumes = db.query(Resume).count()
        total_apps = db.query(Application).filter(Application.status == "Applied").count() 
        
        col1.metric("Opportunities Found", total_jobs, delta="Total Scraped")
        col2.metric("Talent Profiles", total_resumes, delta="Active Resumes")
        col3.metric("Applications Fire", total_apps, delta=f"{round((total_apps/total_jobs)*100 if total_jobs else 0, 1)}% Conversion")
        
        st.markdown("---")
        
        # 2. CHARTS & HISTORY
        c1, c2 = st.columns([2, 1])
        
        with c1:
            st.subheader("Application History")
            # Get successful applications
            apps = db.query(Application, Job).join(Job, Application.job_id == Job.id).filter(Application.status == "Applied").limit(50).all()
            
            if apps:
                data = []
                for app, job in apps:
                    data.append({
                        "Date": app.applied_at.strftime("%Y-%m-%d"),
                        "Company": job.company,
                        "Job Title": job.title,
                        "Portal": job.source
                    })
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No successful applications yet. Go to Auto-Apply!")
                
        with c2:
            st.subheader("Recent Activity")
            # Show last 5 logs or app status
            recent_apps = db.query(Application).order_by(Application.applied_at.desc()).limit(5).all()
            if recent_apps:
                for a in recent_apps:
                     # Fetch job details
                     j = db.query(Job).get(a.job_id)
                     title = j.title if j else f"Job #{a.job_id}"
                     company = f" at {j.company}" if j and j.company else ""
                     st.write(f"🕒 {a.applied_at.strftime('%H:%M')} - Applied to **{title}**{company}")
            else:
                st.info("No activity yet.")

        st.subheader("Portal System Status")
        statuses = db.query(PortalStatus).all()
        if statuses:
            st.dataframe(pd.DataFrame([{"Portal": s.portal_name, "Status": s.status, "Last Scraped": s.last_scraped} for s in statuses]), use_container_width=True)

    elif menu == "🚀 Job Pilot":
        # --- 1. FLIGHT DECK HEADER ---
        if 'mission_role' not in st.session_state: st.session_state['mission_role'] = ""
        if 'mission_loc' not in st.session_state: st.session_state['mission_loc'] = ""
        
        # --- RESUME LOGIC (PRE-FETCH) ---
        resumes = db.query(Resume).all()
        res_opts = {r.name: r.id for r in resumes} if resumes else {}
        active_res_index = 0

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
        
        # MISSION CONTROL PANEL
        with st.container(border=True):
            st.markdown("##### 🛠️ Mission Configuration")
            c1, c2, c3 = st.columns([2, 2, 2])
            
            # Persistent Inputs
            role = c1.text_input("Target Role", value=st.session_state['mission_role'], placeholder="e.g. Python Developer", key="pilot_role")
            loc = c2.text_input("Location", value=st.session_state['mission_loc'], placeholder="e.g. Remote", key="pilot_loc")
            
            # Resume Select
            if resumes:
                sel_res_name = c3.selectbox("Active Identity (Resume)", list(res_opts.keys()))
                sel_res_id = res_opts[sel_res_name]
            else:
                c3.error("❌ No Identity Found")
                sel_res_id = None
        
        # Save Sync State
        st.session_state['mission_role'] = role
        st.session_state['mission_loc'] = loc
        
        # PORTAL SELECTOR
        all_p = ["LinkedIn", "Naukri", "Indeed", "Shine", "Foundit", "Internshala", "IIMJobs", "Wellfound", "Freshersworld", "Glassdoor"]
        sel_portals = st.pills("Active Channels", all_p, default=["LinkedIn"], selection_mode="multi")

        st.write("")
        st.write("")

        # --- THE BIG BUTTON ---
        c_btn, c_term = st.columns([1, 2])
        
        with c_btn:
            st.markdown("### Ready to Launch?")
            st.markdown("Initiate the full autonomous loop: Login Check -> Market Scan -> Profile Match -> Auto-Apply.")
            
            if st.button("🔥 ENGAGE HYPER-DRIVE", type="primary", use_container_width=True):
                missing = []
                if not role: missing.append("Target Role")
                if not loc: missing.append("Location")
                if not sel_res_id: missing.append("Active Resume")
                if not sel_portals: missing.append("Active Portals")
                
                if missing:
                    st.error(f"⚠️ MISSION ABORTED. Missing: {', '.join(missing)}")
                else:
                    applier = AutoApplier()
                    st.session_state['pilot_running'] = True
                    start_time = datetime.utcnow()
                    
                    # SYSTEM TERMINAL
                    with c_term:
                         terminal = st.status("👨‍💻 Pilot Terminal Active", expanded=True)
                         terminal.write("Initializing Hyper-Drive Sequence...")
                         time.sleep(1)
                         
                         try:
                             # Using the unified engine with USER SELECTION
                             target_list = sel_portals if sel_portals else None
                             
                             for update in applier.run_hyper_automation(role, loc, sel_res_id, target_portals=target_list):
                                     terminal.write(f"**[{update['step']}]** {update['status']}")
                                     if update['step'] == "Finished":
                                         terminal.update(label="✅ Mission Complete", state="complete", expanded=False)
                                         st.success("Hyper-Drive Sequence Concluded Successfully.")
                                         st.balloons()
                                         
                                         # --- MISSION REPORT ---
                                         st.subheader("📝 Mission Report")
                                         report_apps = db.query(Application, Job).join(Job, Application.job_id == Job.id)\
                                             .filter(Application.applied_at >= start_time).all()
                                         
                                         if report_apps:
                                             rpt_data = []
                                             for app, job in report_apps:
                                                 # Simple UTC to Local offset (User is in India +5:30)
                                                 from datetime import timedelta
                                                 local_time = app.applied_at + timedelta(hours=5, minutes=30)
                                                 rpt_data.append({
                                                     "Role": job.title,
                                                     "Company": job.company,
                                                     "Status": app.status,
                                                     "Time": local_time.strftime("%H:%M:%S")
                                                 })
                                             st.dataframe(pd.DataFrame(rpt_data), use_container_width=True)
                                         else:
                                             st.info("No applications were sent during this mission.")
                                             
                         except Exception as e:
                             terminal.update(label="❌ Mission Failed", state="error")
                             st.error(f"Critical Failure: {e}")
        
        with c_term:
            if 'pilot_running' not in st.session_state:
                st.info("👈 System Standby. Waiting for command.")

        st.divider()

        # --- 2. LIVE RADAR (Results) ---
        st.subheader("📡 Live Radar (Recent Finds)")
        
        # Connection Health Check (Visual Only)
        st.caption(f"Monitoring {len(sel_portals)} Channels")
        
        # JOB LIST
        jobs = db.query(Job).order_by(Job.scraped_date.desc()).limit(20).all()
        
        if not jobs:
            st.info("Radar is clear. Engage Hyper-Drive to populate.")
        else:
             for job in jobs:
                 c_info, c_act = st.columns([5, 1])
                 
                 with c_info:
                     st.markdown(f"**{job.title}** ")
                     st.caption(f"{job.company} • {job.location} • {job.source}")

                 with c_act:
                     is_busy = st.session_state.get('pilot_running', False)
                     btn_label = "Pilot Busy" if is_busy else "Apply"
                     
                     if st.button(btn_label, key=f"apply_{job.id}", use_container_width=True, disabled=is_busy):
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
                 st.divider()

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
                    https://hirelink.ai/register?ref={user.referral_code}
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
        st.subheader("💰 Rewards Overview")
        c1, c2, c3 = st.columns(3)
        c1.metric("Friends Reached", user.referral_count, delta="Total")
        c2.metric("Active Referrals", db.query(backend.database.AppUser).filter(backend.database.AppUser.referred_by_id == user.id, backend.database.AppUser.subscription_plan != "TRIAL").count(), delta="Paying")
        # Estimate total earned (Commissions paid out + balance)
        total_credits = db.query(func.sum(backend.database.ReferralTransaction.amount)).filter(backend.database.ReferralTransaction.referrer_id == user.id).scalar() or 0
        c3.metric("Service Credits", f"₹ {round(total_credits, 2)}", delta="Applied to bill")

        st.info(f"✨ You have **₹{round(user.earnings_balance, 2)}** in credits ready for your next renewal!")

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
        st.header("👤 Pilot Profile")
        
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
            st.subheader("Resume Manager")
            uploaded_file = st.file_uploader("Upload Resume (PDF)", type="pdf")
            if uploaded_file:
                file_path = os.path.join("data/resumes", uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                parser = ResumeParser()
                resume = parser.parse_and_save(file_path)
                if resume:
                    st.success("Resume parsed successfully!")
                    st.json(resume.parsed_data)
                    
            st.subheader("Saved Resumes")
            resumes = db.query(Resume).all()
            for r in resumes:
                with st.expander(f"{r.name} - {r.email}"):
                    c1, c2 = st.columns([4, 1])
                    with c1:
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

                    with c2:
                        # DELETE CONFIRMATION POPOVER
                        # Using st.popover (requires Streamlit 1.33+)
                        # If older, we fallback to logic or just assume updated env (User has 'vibe coding' enabled)
                        try:
                            with st.popover("🗑️ Delete", help="Permanently delete this resume"):
                                st.write("Are you sure?")
                                if st.button("🚨 Yes, Delete", key=f"conf_del_{r.id}", type="primary"):
                                    # 1. Delete File
                                    if r.file_path and os.path.exists(r.file_path):
                                        try:
                                            os.remove(r.file_path)
                                        except: pass
                                    
                                    # 2. Delete DB Record
                                    db.delete(r)
                                    db.commit()
                                    st.toast("Resume deleted successfully!", icon="🗑️")
                                    time.sleep(1)
                                    st.rerun()
                        except AttributeError:
                            # Fallback for older Streamlit
                            if st.button("🗑️ Delete (Confirm)", key=f"del_res_{r.id}"):
                                # ... (Same delete logic)
                                if r.file_path and os.path.exists(r.file_path): 
                                    try: os.remove(r.file_path) 
                                    except: pass
                                db.delete(r)
                                db.commit()
                                st.rerun()

        # --- TAB 2: SMART ANSWERS ---
        with tab_smart:
            st.subheader("Knowledge Base")
            st.markdown("This is the **brain** of your agent. The more questions you answer here, the accurately it can fill forms.")
            st.info("ℹ️ **Note**: You may encounter similar or duplicate questions. Please answer them all—redundancy helps the AI apply correctly to different portals.")
            
            with st.form("smart_answers_form"):
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
                                    
                                val = st.text_input(label, value=q.answer or "", key=f"sa_qa_{q.id}", help=help_text)
                                q.answer = val
                                
                st.write("")
                c1, c2 = st.columns([3, 1])
                if c2.form_submit_button("💾 Save All Changes", type="primary", use_container_width=True):
                    db.commit()
                    st.toast("Smart Answers saved successfully!", icon="✅")
                    time.sleep(1)
                    st.rerun()

        # --- TAB 3: PORTAL KEYS (CREDENTIALS) ---
        with tab_keys:
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
                 
                 st.write("")
                 if st.form_submit_button("💾 Save Credentials", type="primary", use_container_width=True):
                     updated_count = 0
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
                     
                     db.commit()
                     st.success(f"Successfully saved credentials for {updated_count} portals!")
                     time.sleep(1.5)
                     st.rerun()

    # --- GLOBAL SIDEBAR FOOTER (Always Visible) ---
    with st.sidebar:
        st.markdown("---")
        if st.button("🔴 Reset App State (Debug)", use_container_width=True):
             # 1. Wipe Session
             for key in list(st.session_state.keys()):
                 del st.session_state[key]
             
             # 2. Wipe User Data (to prevent auto-login loop)
             from backend.database import AppUser, Resume
             try:
                 db.query(AppUser).delete()
                 db.query(Resume).delete()
                 db.commit()
                 st.toast("Database Wiped", icon="🗑️")
             except Exception as e:
                 st.error(f"Reset Failed: {e}")
                 
             st.rerun()
        st.caption(f"HireLink v1.1 (Live)")

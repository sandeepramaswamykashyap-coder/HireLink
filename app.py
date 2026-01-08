import streamlit as st
import pandas as pd
import threading
import backend.database # Import module directly
# importlib.reload logic removed for stability
import sys
import importlib
# FORCE RELOAD of LLM Client to pick up model fix
if 'backend.utils.llm_client' in sys.modules:
    del sys.modules['backend.utils.llm_client']
if 'backend.agents.job_analyzer' in sys.modules:
    del sys.modules['backend.agents.job_analyzer']

from backend.database import init_db, get_db, Job, Resume, Application, PortalStatus, QuestionAnswer
# FORCE DB INIT to create new tables
init_db()
from backend.scrapers.naukri import NaukriScraper
from backend.scrapers.linkedin import LinkedInScraper
from backend.scrapers.indeed import IndeedScraper
from backend.scrapers.others import (
    ShineScraper, GlassdoorScraper, FounditScraper, 
    IntershalaScraper, IIMJobsScraper, FreshersworldScraper, WellfoundScraper
)
import backend.agents.resume_parser
import backend.agents.auto_applier
from backend.agents.resume_parser import ResumeParser
from backend.agents.job_matcher import JobMatcher
from backend.agents.auto_applier import AutoApplier
from backend.agents.job_analyzer import JobAnalyzer
import os
import time

st.set_page_config(page_title="Hire Link", layout="wide")

# Load Custom CSS
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

try:
    local_css("assets/style.css")
except:
    pass # Fallback if file missing

st.title("Hire Link")

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
        st.error(f"Failed to launch browser: {e}")

# --- ONBOARDING LOGIC ---
def render_onboarding():
    st.markdown("""
    <style>
        /* Container Polish - Lighter & Elevated */
        [data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #383a47 !important; /* SIGNIFICANTLY LIGHTER */
            border: 1px solid #5a5a5a !important;
            box-shadow: 0 8px 24px rgba(0,0,0,0.4) !important;
            padding: 2.5rem !important;
        }
        .step-header {
            text-align: center;
            margin-bottom: 2rem;
        }
        .step-kicker {
            color: #94a3b8;
            text-transform: uppercase;
            font-size: 0.8rem;
            letter-spacing: 1px;
            font-weight: 600;
        }
        .step-title {
            font-size: 1.5rem;
            font-weight: 700;
            color: white;
            margin-top: 0.5rem;
            margin-bottom: 1rem;
        }
        .step-desc {
            color: #94a3b8;
            font-size: 1rem;
            line-height: 1.5;
            max-width: 500px;
            margin: auto;
        }
        .stTextInput > label, .stSelectbox > label {
            color: #e2e8f0 !important;
            font-weight: 600;
        }
        div[data-testid="stForm"] {
            border: none;
            padding: 0;
        }
    </style>
    """, unsafe_allow_html=True)
    
    if 'onboarding_step' not in st.session_state:
        st.session_state['onboarding_step'] = 1
    
    step = st.session_state['onboarding_step']
    total_steps = 5
    progress = step / total_steps
    
    # Progress Bar (Centered above card)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.progress(progress)
        st.caption(f"Step {step} of {total_steps}")
    
    # Layout: [Spacer] [Card] [Spacer]
    # To mimic a 500px card, we use strict column ratios.
    main_col1, main_col2, main_col3 = st.columns([1, 2, 1])
    
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
                name = st.text_input("FULL NAME *", placeholder="e.g. Sandeep Kashyap")
                email = st.text_input("EMAIL *", placeholder="e.g. sandeep@example.com")
                loc = st.text_input("CURRENT LOCATION *", placeholder="e.g. Bangalore, India")
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

        # --- STEP 2: RESUME ---
        elif step == 2:
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
                 st.session_state['onboarding_step'] = 1
                 st.rerun()
                 
            if uploaded_file:
                # Auto-Advance Logic
                if st.button("NEXT STEP", type="primary", use_container_width=True):
                     file_path = os.path.join("data/resumes", uploaded_file.name)
                     with open(file_path, "wb") as f:
                         f.write(uploaded_file.getbuffer())
                     
                     with st.spinner("Analyzing resume..."):
                         parser = ResumeParser()
                         resume = parser.parse_and_save(file_path) # Saves Resume to DB
                         st.session_state['ob_resume_id'] = resume.id
                     
                     st.session_state['onboarding_step'] = 3
                     st.rerun()
        # --- STEP 3: PREFERENCES (Roles/Locs) ---
        elif step == 3:
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
                         st.session_state['onboarding_step'] = 4
                         st.rerun()
                    else:
                        st.error("At least one Role and Location is required.")
                        
            if st.button("BACK", use_container_width=True):
                st.session_state['onboarding_step'] = 2
                st.rerun()

        # --- STEP 4: WORK STYLE ---
        elif step == 4:
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
                        is_admin=is_first_user # Grant Admin to first user
                    )
                    db.add(user)
                    db.commit()
                    st.session_state['onboarding_step'] = 5
                    st.rerun()
            
            if st.button("BACK", use_container_width=True):
                 st.session_state['onboarding_step'] = 3
                 st.rerun()
    
        # --- STEP 5: CONNECT (Technical Step) ---
        elif step == 5:
            st.markdown("""
            <div class="step-header">
                <div class="step-kicker">FINAL STEP</div>
                <div class="step-title">Connect Your Accounts</div>
                <div class="step-desc">Launch the secure browser to login once. We save the session cookies locally.</div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("🚀 Launch Secure Login Browser", use_container_width=True):
                launch_login_browser()
                
            st.write("")
            if st.button("I'm All Set - Go to Dashboard 🎉", type="primary", use_container_width=True):
                 user = db.query(backend.database.AppUser).first()
                 if user:
                     user.is_onboarded = True
                     db.commit()
                     st.balloons()
                     st.rerun()

def run_scraper(portals, keywords, location):
    # Ensure iterability
    if isinstance(portals, str): portals = [portals]
    
    total_new_jobs = 0
    from backend.database import SessionLocal, Job
    db = SessionLocal()
    initial_count = db.query(Job).count()
    db.close()
    
    for p_name in portals:
        scraper = None
        try:
            if p_name == "Naukri": scraper = NaukriScraper()
            elif p_name == "LinkedIn": scraper = LinkedInScraper()
            elif p_name == "Indeed": scraper = IndeedScraper()
            elif p_name == "Shine": scraper = ShineScraper()
            elif p_name == "Glassdoor": scraper = GlassdoorScraper()
            elif p_name == "Foundit": scraper = FounditScraper()
            elif p_name == "Intershala": scraper = IntershalaScraper()
            elif p_name == "IIMJobs": scraper = IIMJobsScraper()
            elif p_name == "Freshersworld": scraper = FreshersworldScraper()
            elif p_name == "Wellfound": scraper = WellfoundScraper()
            
            if scraper:
                with st.spinner(f"Scraping {p_name}..."):
                    try:
                        scraper.search_jobs(keywords, location)
                    except Exception as e:
                        print(f"Error scraping {p_name}: {e}")
        except: pass
        
    db = SessionLocal()
    final_count = db.query(Job).count()
    db.close()
    
    return max(0, final_count - initial_count)

# --- MAIN CONTROLLER ---
try:
    user = db.query(backend.database.AppUser).filter_by(is_onboarded=True).first()
except:
    user = None # Handle table not existing edge case if init failed

if not user:
    render_onboarding()
else:
    # Sidebar
    st.sidebar.header("Navigation")
    is_admin = getattr(user, 'is_admin', False)
    st.sidebar.markdown(f"**👤 {user.name}**{' (Admin)' if is_admin else ''}")
    
    # TOUR TOGGLE
    tour_mode = st.sidebar.toggle("🗺️ Enable Tour Mode", value=False, help="Turn this on to see a guided walkthrough of features.")
    
    if not hasattr(user, 'is_admin'):
        st.error("⚠️ **SYSTEM UPDATE PENDING** ⚠️")
        st.warning("Please restart your terminal to activate Admin features.")
    
    if tour_mode:
        st.sidebar.info("👈 **Navigation Menu:** Switch between 'Job Search' (Finding Jobs) and 'Auto-Apply' (Matching & Applying).")
    
    nav_options = ["Dashboard", "Job Search", "Resumes", "Auto-Apply", "Smart Answers", "Login & Sessions"]
    if is_admin:
        nav_options.append("Admin Console")
        
    menu = st.sidebar.radio("Go to", nav_options)

    # ... (Other menus same) ...
    
    if menu == "Admin Console":
        st.header("🛡️ Admin Console")
        st.markdown("Manage users and system health.")
        
        st.subheader("Registered Users")
        users = db.query(backend.database.AppUser).all()
        
        for u in users:
            with st.expander(f"{u.name} ({u.email}) {'👑 ADMIN' if u.is_admin else ''}", expanded=True):
                c1, c2, c3 = st.columns(3)
                c1.write(f"**Location:** {u.curr_loc}")
                c2.write(f"**Role Targets:** {u.target_roles}")
                c3.write(f"**Joined:** {u.created_at.strftime('%Y-%m-%d')}")
                
                if st.button("🗑️ Delete User", key=f"del_{u.id}"):
                    if u.id == user.id:
                        st.error("You cannot delete yourself!")
                    else:
                        db.delete(u)
                        db.commit()
                        st.success(f"Deleted {u.name}")
                        st.rerun()
                        
        st.markdown("---")
        st.markdown("---")
        st.subheader("System Stats")
        st.metric("Total Jobs in DB", db.query(Job).count())
        st.metric("Total Applications Sent", db.query(Application).count())

        st.markdown("---")
        st.subheader("⚙️ System Configuration")
        
        # API KEY MANAGEMENT
        current_key = os.getenv("GEMINI_API_KEY", "")
        with st.form("config_form"):
            st.markdown("**LLM Settings (Gemini)**")
            st.caption("Required for Smart Resume Parsing and Cover Letters.")
            
            new_key = st.text_input("Gemini API Key", value=current_key if current_key else "", type="password", placeholder="AIzaSy...")
            
            if st.form_submit_button("Save Configuration"):
                if new_key:
                    # simplistic .env writer
                    env_path = ".env"
                    lines = []
                    if os.path.exists(env_path):
                        with open(env_path, "r") as f:
                            lines = f.readlines()
                    
                    # Remove existing key
                    lines = [l for l in lines if "GEMINI_API_KEY" not in l]
                    lines.append(f"GEMINI_API_KEY={new_key}\n")
                    
                    with open(env_path, "w") as f:
                        f.writelines(lines)
                        
                    os.environ["GEMINI_API_KEY"] = new_key
                    st.success("API Key Saved! Please restart the app/terminal for full effect (some modules load env at startup).")
                else:
                    st.info("Key cleared.")

# ... (Rest of app) ...

    if menu == "Dashboard":
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
                     st.write(f"🕒 {a.applied_at.strftime('%H:%M')} - Applied to {a.job_id}")
            else:
                st.info("No activity yet.")

        st.subheader("Portal System Status")
        statuses = db.query(PortalStatus).all()
        if statuses:
            st.dataframe(pd.DataFrame([{"Portal": s.portal_name, "Status": s.status, "Last Scraped": s.last_scraped} for s in statuses]), use_container_width=True)

    elif menu == "Job Search":
        st.header("🔍 Job Search Agent")
        
        if tour_mode:
            st.info("💡 **Walkthrough:** This is where you find NEW jobs. Enter your role and location, select portals, and click Start.")
        
        with st.form("search_form"):
            col1, col2 = st.columns(2)
            
            if tour_mode:
                col1.caption("👉 **Target Role:** e.g., 'Python Developer'")
                col2.caption("👉 **Target City:** e.g., 'Remote' or 'Bangalore'")
                
            keywords = col1.text_input("Keywords", placeholder="e.g. Python Developer")
            location = col2.text_input("Location", placeholder="e.g. Bangalore")
            
            # Neat Widget Arrangement (Pills)
            st.markdown("##### 🌐 Select Job Portals")
            
            # Status Mapping for UI
            portal_map = {
                "LinkedIn": "LinkedIn ✅",
                "IIMJobs": "IIMJobs ✅",
                "Shine": "Shine ✅",
                "Foundit": "Foundit ✅",
                "Intershala": "Internshala ✅",
                "Freshersworld": "Freshersworld ✅",
                "Glassdoor": "Glassdoor ✅",
                "Wellfound": "Wellfound ⚠️",
                "Indeed": "Indeed ⚠️", 
                "Naukri": "Naukri ❌"
            }
            
            all_portals_ui = list(portal_map.values())
            
            with st.container(border=True):
                 st.caption("✅ Recommended  |  ⚠️ Unstable  |  ❌ Crashing  |  🚧 Coming Soon")
                 selected_portals_ui = st.pills(
                     "Portals",
                     options=all_portals_ui,
                     default=["LinkedIn ✅"],
                     selection_mode="multi",
                     label_visibility="collapsed"
                 )
            
            st.write("") # Spacer
            submitted = st.form_submit_button("Start Scraping", type="primary", use_container_width=True)
            
        if submitted:
            # Clean up UI selection to get backend keys
            # "LinkedIn ✅" -> "LinkedIn"
            active_portals = [p.split(" ")[0] for p in selected_portals_ui] if selected_portals_ui else []
            
            if not keywords or not location:
                 st.error("Please enter Keywords and Location")
            elif not active_portals:
                 st.error("Please select at least one portal")
            else:
                 with st.spinner(f"Scraping {len(active_portals)} portals for '{keywords}' in '{location}'..."):
                     # Run Scraper (Synchronously for now to ensure data is ready)
                     count = run_scraper(active_portals, keywords, location)
                     if count > 0:
                         st.success(f"Found {count} new jobs! 🎉")
                     else:
                         st.info("Scraping complete. No *new* jobs added (duplicates skipped). Check the list below for results. ⬇️")
                     
                     time.sleep(1.5)
                     st.rerun()
                
        st.markdown("---")
        st.subheader("Latest Scraped Jobs")
        
        # INCREASED LIMIT TO 100
        jobs = db.query(Job).order_by(Job.scraped_date.desc()).limit(100).all()
        
        
        if jobs:
            # --- BULK SELECTION CONTROLS ---
            c_toggle, c_bulk_btn = st.columns([1, 3])
            bulk_mode = c_toggle.toggle("✅ Enable Multi-Select", help="Switch to selection mode to apply to multiple jobs at once.")
            
            tab1, tab2 = st.tabs(["Job Cards", "Table View"])
            
            with tab1:
                default_resume = db.query(Resume).first()
                if not default_resume and (bulk_mode or st.session_state.get('bulk_apply_clicked')):
                     st.error("Please upload a resume first to apply!")
                
                # Constrain Width (Center the cards)
                sp1, center_col, sp2 = st.columns([1, 10, 1])
                
                with center_col:
                    # --- BULK MODE UI ---
                    if bulk_mode:
                        # CONTROLS OUTSIDE FORM (Interactive)
                        c_sel, c_count = st.columns([2, 5])
                        select_all = c_sel.checkbox("Select All Jobs")
                        if select_all:
                            c_count.info(f"✅ {len(jobs)} jobs selected")
                        
                        with st.form("bulk_apply_form"):
                            # TOP BUTTON
                            top_submit = st.form_submit_button("⚡ Apply", type="primary", use_container_width=True, help="Apply to checked jobs", key="bulk_apply_top")
                            
                            # TOP PROGRESS PLACEHOLDERS (Visible when running)
                            top_progress = st.empty()
                            top_status = st.empty()
                            
                            st.divider()
                            
                            selected_job_ids = []
                            
                            # Render Checkbox Cards
                            for job in jobs:
                                with st.container(border=True):
                                    c_chk, c_info = st.columns([0.5, 9.5])
                                    with c_chk:
                                        st.write("") 
                                        # Force re-render by including state in key
                                        chk_key = f"chk_{job.id}_ALL-{select_all}"
                                        if st.checkbox("Select", key=chk_key, value=select_all, label_visibility="collapsed"):
                                            selected_job_ids.append(job.id)
                                    
                                    with c_info:
                                        # Row 1: Title
                                        st.markdown(f"#### {job.title}")
                                        
                                        # Row 2: Company & Location (Gray text)
                                        st.markdown(f"<div style='color:#94a3b8; margin-bottom: 8px;'>🏢 {job.company} &nbsp;•&nbsp; 📍 {job.location}</div>", unsafe_allow_html=True)
                                        
                                        # Row 3: Pills (Source as valid widget-like pill)
                                        # Use the existing 'job-pill' class from CSS
                                        source_pill = f'<span class="job-pill">🔗 {job.source}</span>'
                                        salary_pill = f'<span class="job-pill">💰 {job.salary or "N/A"}</span>'
                                        date_pill = f'<span class="job-pill">📅 {job.posted_date.strftime("%Y-%m-%d") if job.posted_date else "Recent"}</span>'
                                        
                                        st.markdown(f"""
                                        <div style="display: flex; gap: 10px; flex-wrap: wrap; padding-bottom: 12px;">
                                            {source_pill}
                                            {salary_pill}
                                            {date_pill}
                                        </div>
                                        """, unsafe_allow_html=True)
                            
                            st.write("")
                            bottom_submit = st.form_submit_button("⚡ Apply", type="primary", use_container_width=True, help="Apply to checked jobs", key="bulk_apply_bottom")
                            
                            
                            if top_submit or bottom_submit:
                                if not selected_job_ids:
                                    st.warning("No jobs selected.")
                                else:
                                    if not default_resume:
                                        st.error("Resume missing!")
                                    else:
                                        # PROCESS BULK
                                        # Initialize Bottom placeholders too
                                        progress_bar = st.progress(0)
                                        status_text = st.empty()
                                        
                                        success_cnt = 0
                                        applier = AutoApplier()
                                        try:
                                            total = len(selected_job_ids)
                                            for i, jid in enumerate(selected_job_ids):
                                                msg = f"Applying... ({i+1}/{total})"
                                                
                                                # Update BOTH Top and Bottom
                                                status_text.text(msg)
                                                top_status.info(msg) # Use info for better visibility
                                                
                                                progress_val = (i + 1) / total
                                                progress_bar.progress(progress_val)
                                                top_progress.progress(progress_val)
                                                
                                                if applier.apply_to_job(jid, default_resume.id):
                                                    success_cnt += 1
                                            
                                            st.balloons()
                                            success_msg = f"Done! Sent {success_cnt} apps."
                                            st.success(success_msg)
                                            top_status.success(success_msg)
                                            
                                            time.sleep(2)
                                            st.rerun()
                                        finally:
                                            applier.close_browser()

                    # --- STANDARD MODE UI ---
                    else:
                        for job in jobs:
                            # Boxed Card (Restored)
                            with st.container(border=True):
                                # Adjusted ratio to prevent overlap: 3 parts info, 1 part actions
                                c_info, c_actions = st.columns([3, 1])
                                
                                with c_info:
                                    # Row 1: Title
                                    st.markdown(f"#### {job.title}")
                                    
                                    # Row 2: Company & Location
                                    st.markdown(f"<div style='color:#94a3b8; margin-bottom: 8px;'>🏢 {job.company} &nbsp;•&nbsp; 📍 {job.location}</div>", unsafe_allow_html=True)
                                    
                                    # Row 3: Pills (Source, Salary, Date)
                                    source_pill = f'<span class="job-pill">🔗 {job.source}</span>'
                                    salary_pill = f'<span class="job-pill">💰 {job.salary or "N/A"}</span>'
                                    date_pill = f'<span class="job-pill">📅 {job.posted_date.strftime("%Y-%m-%d") if job.posted_date else "Recent"}</span>'
                                    
                                    st.markdown(f"""
                                    <div style="display: flex; gap: 10px; flex-wrap: wrap; padding-bottom: 12px;">
                                        {source_pill}
                                        {salary_pill}
                                        {date_pill}
                                    </div>
                                    """, unsafe_allow_html=True)
                                    
                                with c_actions:
                                    # Action Buttons
                                    key_apply = f"quick_apply_{job.id}"
                                    if st.button("Apply", key=key_apply, use_container_width=True, type="primary"):
                                        if not default_resume:
                                            st.error("No Resume!")
                                        else:
                                            applier = AutoApplier()
                                            st.toast(f"Applying to {job.company}...")
                                            try:
                                                if applier.apply_to_job(job.id, default_resume.id):
                                                     st.success("Applied!")
                                                else:
                                                     st.error("Failed")
                                            except Exception as e:
                                                st.error(f"Err: {e}")
                                            finally:
                                                applier.close_browser()
                                    
                                    # Analyze Button
                                    key_analyze = f"analyze_{job.id}"
                                    if st.button("Analyze Fit 🧠", key=key_analyze, use_container_width=True):
                                        if not default_resume:
                                            st.error("Resume Required")
                                        elif not os.getenv("GEMINI_API_KEY"):
                                            st.error("Add API Key in Admin Console")
                                        else:
                                            with st.spinner("Asking AI Recruiter..."):
                                                analyzer = JobAnalyzer()
                                                result = analyzer.analyze_suitability(job.description or job.title, default_resume.raw_text)
                                                if result:
                                                    st.session_state[f"analysis_{job.id}"] = result
                                                else:
                                                    st.error("Analysis Failed")

                                    # Restore Button Link
                                    st.link_button("View 🔗", job.url, use_container_width=True)
                            
                            # Show Analysis Result (if available)
                            if f"analysis_{job.id}" in st.session_state:
                                res = st.session_state[f"analysis_{job.id}"]
                                if res:
                                    with st.expander(f"🧠 Analysis: {res.get('score', 0)}/100 Match", expanded=True):
                                        st.markdown(f"**Reasoning:** {res.get('match_reason', 'N/A')}")
                                        if res.get('missing_skills'):
                                            st.error(f"**Missing Skills:** {', '.join(res.get('missing_skills'))}")
                                        if res.get('keywords_to_add'):
                                            st.info(f"**Add Keywords:** {', '.join(res.get('keywords_to_add'))}")
            
            with tab2:
                # DataFrame View
                data = [{"Title": j.title, "Company": j.company, "Location": j.location, "Source": j.source, "Date": j.posted_date.strftime('%Y-%m-%d') if j.posted_date else 'Recent', "URL": j.url} for j in jobs]
                st.dataframe(pd.DataFrame(data), use_container_width=True)
                st.caption("Showing last 100 scraped jobs.")
        else:
            st.info("No jobs found yet.")

    elif menu == "Resumes":
        st.header("📄 Resume Manager")
        
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
                st.json(r.parsed_data)

    elif menu == "Auto-Apply":
        st.header("🤖 Auto-Apply Agent")
        
        if tour_mode:
            st.info("💡 **Walkthrough:** This is the 'Sniper' mode. We match your resume against saved jobs to find the best fit.")
        
        # 1. Control Panel
        c1, c2 = st.columns([3, 1])
        with c1:
            if tour_mode: st.caption("👉 **Step 1:** Select which resume to use for matching.")
            resumes = db.query(Resume).all()
            if not resumes:
                st.warning("Please upload a resume first.")
            else:
                resume_options = {f"{r.name} ({r.id})": r.id for r in resumes}
                selected_resume_name = st.selectbox("Select Resume", list(resume_options.keys()))
                selected_resume_id = resume_options[selected_resume_name]
        
        with c2:
            st.write("") # Spacer
            st.write("")
            if tour_mode: st.caption("👉 **Step 2:** Run the AI Matcher.")
            find_btn = st.button("Find Matches", use_container_width=True)

        if find_btn and resumes:
            matcher = JobMatcher()
            # INCREASED MATCH LIMIT TO 50
            matches = matcher.match_jobs(selected_resume_id, limit=50)
            st.session_state['matches'] = matches
            st.success(f"Found {len(matches)} matches!")
            
        if 'matches' in st.session_state:
            
            # 2. BULK ACTION AREA (Top Right Prominent)
            st.markdown("---")
            col_info, col_btn = st.columns([2, 2])
            with col_info:
                st.subheader(f"Ready to Apply: {len(st.session_state['matches'])} Jobs")
            with col_btn:
                if tour_mode: st.caption("👉 **Step 3:** Click this to apply to ALL matched jobs sequentially.")
                # BIG PRIMARY BUTTON
                if st.button(f"🚀 START AUTO-APPLY ({len(st.session_state['matches'])})", type="primary", use_container_width=True):
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    success_count = 0
                    
                    applier = AutoApplier()
                    try:
                        for i, m in enumerate(st.session_state['matches']):
                            job = m['job']
                            status_text.text(f"Applying to {job.company} ({i+1}/{len(st.session_state['matches'])})...")
                            if applier.apply_to_job(job.id, selected_resume_id):
                                success_count += 1
                            progress_bar.progress((i + 1) / len(st.session_state['matches']))
                        
                        status_text.text(f"Completed! Applied to {success_count} jobs.")
                        st.balloons()
                    finally:
                        applier.close_browser()

            st.markdown("---")
            st.subheader("Match Breakdown")
                
            for m in st.session_state['matches']:
                    job = m['job']
                    score = m['score']
                    
                    # PREMIUM CARD VIEW
                    st.markdown(f"""
                    <div class="job-card">
                        <div class="match-score-badge">{score}% Match</div>
                        <div class="job-title">{job.title}</div>
                        <div class="job-company">
                            <span>🏢 {job.company}</span>
                        </div>
                        <div class="job-meta">
                            <div class="job-pill">📍 {job.location}</div>
                            <div class="job-pill">💰 {job.salary}</div>
                            <div class="job-pill">🔗 {job.source}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Action Buttons
                    col1, col2 = st.columns([1, 4])
                    if col1.button("Apply Now", key=f"apply_{job.id}"):
                        applier = AutoApplier()
                        try:
                            if applier.apply_to_job(job.id, selected_resume_id):
                                st.balloons()
                                st.success(f"Successfully applied to {job.company}!")
                            else:
                                st.error("Application failed.")
                        finally:
                            applier.close_browser()

    elif menu == "Smart Answers":
        st.header("🧠 Smart Answer Memory")
        st.info("Train your bot! Fill these out so it can answer questions for you.")
        
        # Group by Category
        qa_list = db.query(QuestionAnswer).all()
        categories = set([q.category for q in qa_list])
        
        for cat in categories:
            with st.expander(f"{cat.title()} Questions", expanded=True):
                cat_qs = [q for q in qa_list if q.category == cat]
                for q in cat_qs:
                    new_ans = st.text_input(f"{q.question}", value=q.answer, key=f"qa_{q.id}")
                    if new_ans != q.answer:
                        q.answer = new_ans
                        db.commit()
                        st.toast(f"Updated answer for {q.question}")
                        
        st.subheader("Add New Question Rule")
        with st.form("add_qa"):
            new_q = st.text_input("Question contains text (e.g., 'Python Experience')")
            new_a = st.text_input("Answer to give (e.g., '5')")
            new_c = st.selectbox("Category", ["experience", "personal", "legal", "education"])
            if st.form_submit_button("Add Rule"):
                if new_q and new_a:
                    db.add(QuestionAnswer(question=new_q, answer=new_a, category=new_c))
                    db.commit()
                    st.success("Added new rule!")
                    st.rerun()

    elif menu == "Login & Sessions":
        st.header("🔑 Session Manager")
        st.markdown("""
        **To apply successfully, the bot needs to be logged in.**
        
        1. Click the button below to open a Chrome window.
        2. Login to **Naukri**, **LinkedIn**, and **Indeed** manually.
        3. Once logged in, close the browser window.
        4. The bot will reuse your session cookies for scraping and applying.
        """)
        
        if st.button("Launch Browser for Login"):
            launch_login_browser()

# Force Reload Triggered by Agent

import streamlit as st
import pandas as pd
import threading
import backend.database # Import module directly
# importlib.reload logic removed for stability
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
    import importlib
    importlib.reload(selenium_utils) # Force reload
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
        .onboarding-container { max-width: 600px; margin: auto; padding: 2rem; }
        .step-title { font-size: 2rem; font-weight: 800; color: #3B82F6; margin-bottom: 1rem; }
        .step-desc { font-size: 1.1rem; color: #94A3B8; margin-bottom: 2rem; }
    </style>
    """, unsafe_allow_html=True)
    
    # Step 1: Create Profile
    if 'onboarding_step' not in st.session_state:
        st.session_state['onboarding_step'] = 1

    if st.session_state['onboarding_step'] == 1:
        st.markdown('<div class="onboarding-container">', unsafe_allow_html=True)
        st.markdown('<div class="step-title">Welcome to Hire Link</div>', unsafe_allow_html=True)
        st.markdown('<div class="step-desc">Let\'s get you set up with your personal local AI recruiter.</div>', unsafe_allow_html=True)
        
        with st.form("profile_setup"):
            name = st.text_input("What is your name?")
            email = st.text_input("Your Email (for applications)")
            submitted = st.form_submit_button("Next: Upload Resume ➔")
            
            if submitted and name and email:
                # Create Profile
                # Access AppUser dynamically to avoid caching issues
                user = backend.database.AppUser(name=name, email=email)
                db.add(user)
                db.commit()
                st.session_state['user_id'] = user.id
                st.session_state['onboarding_step'] = 2
                st.rerun() # Use standard rerun
        st.markdown('</div>', unsafe_allow_html=True)

    # Step 2: Upload Resume
    elif st.session_state['onboarding_step'] == 2:
        st.markdown('<div class="onboarding-container">', unsafe_allow_html=True)
        st.markdown('<div class="step-title">Upload your Resume</div>', unsafe_allow_html=True)
        st.markdown('<div class="step-desc">The AI will parse this to match you with jobs.</div>', unsafe_allow_html=True)
        
        uploaded_file = st.file_uploader("Upload PDF Resume", type="pdf")
        if uploaded_file:
            file_path = os.path.join("data/resumes", uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            with st.spinner("Analyzing your resume..."):
                parser = ResumeParser()
                resume = parser.parse_and_save(file_path)
                if resume:
                    st.success(f"Great! We extracted keys skills: {', '.join(resume.parsed_data.get('skills', [])[:5])}")
                    time.sleep(2)
                    st.session_state['onboarding_step'] = 3
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # Step 3: Connect Accounts
    elif st.session_state['onboarding_step'] == 3:
        st.markdown('<div class="onboarding-container">', unsafe_allow_html=True)
        st.markdown('<div class="step-title">Connect Your Accounts</div>', unsafe_allow_html=True)
        st.markdown('<div class="step-desc">Launch the secure browser to login to your job portals once. We save the session cookies locally.</div>', unsafe_allow_html=True)
        
        if st.button("🚀 Launch Secure Login Browser"):
            launch_login_browser()
            
        st.markdown("---")
        if st.button("I'm Logged In - Finish Setup 🎉"):
             user = db.query(backend.database.AppUser).first() # Assuming single user for now
             if user:
                 user.is_onboarded = True
                 db.commit()
                 st.balloons()
                 time.sleep(2)
                 st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

def run_scraper(scraper_name, keywords, location):
    scraper = None
    if scraper_name == "Naukri": scraper = NaukriScraper()
    elif scraper_name == "LinkedIn": scraper = LinkedInScraper()
    elif scraper_name == "Indeed": scraper = IndeedScraper()
    elif scraper_name == "Shine": scraper = ShineScraper()
    elif scraper_name == "Glassdoor": scraper = GlassdoorScraper()
    elif scraper_name == "Foundit": scraper = FounditScraper()
    elif scraper_name == "Intershala": scraper = IntershalaScraper()
    elif scraper_name == "IIMJobs": scraper = IIMJobsScraper()
    elif scraper_name == "Freshersworld": scraper = FreshersworldScraper()
    elif scraper_name == "Wellfound": scraper = WellfoundScraper()
    
    if scraper:
        scraper.search_jobs(keywords, location)

# --- MAIN CONTROLLER ---
try:
    # Use Access UserProfile dynamically
    user = db.query(backend.database.AppUser).filter_by(is_onboarded=True).first()
except:
    user = None # Handle table not existing edge case if init failed

if not user:
    render_onboarding()
else:
    # Sidebar
    st.sidebar.header("Navigation")
    st.sidebar.markdown(f"**👤 {user.name}**")
    menu = st.sidebar.radio("Go to", ["Dashboard", "Job Search", "Resumes", "Auto-Apply", "Smart Answers", "Login & Sessions"])

    if menu == "Dashboard":
        st.header("📊 Dashboard")
        
        col1, col2, col3 = st.columns(3)
        
        total_jobs = db.query(Job).count()
        total_resumes = db.query(Resume).count()
        total_apps = db.query(Application).count()
        
        col1.metric("Total Jobs", total_jobs)
        col2.metric("Resumes", total_resumes)
        col3.metric("Applications Sent", total_apps)
        
        st.subheader("Portal Status")
        statuses = db.query(PortalStatus).all()
        if statuses:
            status_data = [{"Portal": s.portal_name, "Status": s.status, "Last Scraped": s.last_scraped, "Jobs Found": s.total_jobs_found} for s in statuses]
            st.dataframe(pd.DataFrame(status_data), use_container_width=True)
        else:
            st.info("No scraper activity yet.")

    elif menu == "Job Search":
        st.header("🔍 Job Search Agent")
        
        with st.form("search_form"):
            col1, col2 = st.columns(2)
            keywords = col1.text_input("Keywords (e.g., Python Developer)")
            location = col2.text_input("Location (e.g., Bangalore)")
            portals = st.multiselect(
                "Select Portals", 
                ["Naukri", "LinkedIn", "Indeed", "Shine", "Glassdoor", "Foundit", "Intershala", "IIMJobs", "Freshersworld", "Wellfound"], 
                default=["Naukri"]
            )
            submitted = st.form_submit_button("Start Scraping")
            
        if submitted:
            st.success(f"Started scraping for '{keywords}' in '{location}'...")
            # Run in threads
            for p in portals:
                t = threading.Thread(target=run_scraper, args=(p, keywords, location))
                t.start()
                st.info(f"Launched {p} scraper in background...")
                
        st.subheader("Latest Jobs")
        jobs = db.query(Job).order_by(Job.scraped_date.desc()).limit(20).all()
        if jobs:
            for job in jobs:
                st.markdown(f"""
                <div class="job-card">
                    <div class="job-title">{job.title}</div>
                    <div class="job-company">{job.company}</div>
                    <div class="job-meta">
                        <span>📍 {job.location}</span>
                        <span>🔗 {job.source}</span>
                        <span>💰 {job.salary}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("Link", key=f"link_{job.id}"):
                    # We can't open tabs easily from streamlit python, so we just show url
                    st.write(f"URL: {job.url}")
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
        
        # Select Resume
        resumes = db.query(Resume).all()
        if not resumes:
            st.warning("Please upload a resume first.")
        else:
            resume_options = {f"{r.name} ({r.id})": r.id for r in resumes}
            selected_resume_name = st.selectbox("Select Resume", list(resume_options.keys()))
            selected_resume_id = resume_options[selected_resume_name]
            
            if st.button("Find Matches"):
                matcher = JobMatcher()
                matches = matcher.match_jobs(selected_resume_id, limit=20)
                st.session_state['matches'] = matches
                st.success(f"Found {len(matches)} matches!")
                
            if 'matches' in st.session_state:
                st.subheader("Results")
                
                # Bulk Apply Section
                if st.button(f"🚀 Auto-Apply to All {len(st.session_state['matches'])} Top Matches"):
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    success_count = 0
                    
                    applier = AutoApplier()
                    try:
                        for i, m in enumerate(st.session_state['matches']):
                            job = m['job']
                            score = m['score']
                            status_text.text(f"Applying to {job.company} ({i+1}/{len(st.session_state['matches'])})...")
                            
                            if applier.apply_to_job(job.id, selected_resume_id):
                                success_count += 1
                            
                            progress_bar.progress((i + 1) / len(st.session_state['matches']))
                        
                        status_text.text(f"Completed! Successfully applied to {success_count} jobs.")
                        st.balloons()
                    finally:
                        applier.close_browser()
                
                st.markdown("---")
                st.subheader("Individual Matches")
                
                for m in st.session_state['matches']:
                    job = m['job']
                    score = m['score']
                    
                    # Custom Card View
                    st.markdown(f"""
                    <div class="job-card">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <div>
                                <div class="job-title">{job.title}</div>
                                <div class="job-company">{job.company}</div>
                            </div>
                            <div class="match-score">{score}% Match</div>
                        </div>
                        <div class="job-meta">
                            <span>📍 {job.location}</span>
                            <span>🔗 {job.source}</span>
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

    elif menu == "Login & Sessions":
        st.header("🔑 Session Manager")
        # ... (keep existing login code logic if you were copying full file, but here we append new menu)
        # This approach is hard with replace_file if I don't see the context.
        # I will replace the MENU definitions first to include "Smart Answers".
        
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

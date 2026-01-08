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
    
    # TOUR TOGGLE
    tour_mode = st.sidebar.toggle("🗺️ Enable Tour Mode", value=False, help="Turn this on to see a guided walkthrough of features.")
    
    if tour_mode:
        st.sidebar.info("👈 **Navigation Menu:** Switch between 'Job Search' (Finding Jobs) and 'Auto-Apply' (Matching & Applying).")
    
    menu = st.sidebar.radio("Go to", ["Dashboard", "Job Search", "Resumes", "Auto-Apply", "Smart Answers", "Login & Sessions"])

    if menu == "Dashboard":
        # ... (Hero Section) ...
    # (Leaving Dashboard lines alone for now, focus on Job Search changes below)
    
# ... (Skipping Dashboard logic to get to Job Search) ...

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
            
            st.markdown("**Select Portals:**")
            if tour_mode:
                st.caption("ℹ️ **Tip:** Naukri and LinkedIn are the best. Select more for volume.")
                
            # Custom 'Pills' Layout using Checkboxes in Columns
            p1, p2, p3, p4 = st.columns(4)
            naukri = p1.checkbox("Naukri", value=True)
            linkedin = p2.checkbox("LinkedIn", value=True)
            indeed = p3.checkbox("Indeed")
            glassdoor = p4.checkbox("Glassdoor")
            
            p5, p6, p7, p8 = st.columns(4)
            shine = p5.checkbox("Shine")
            foundit = p6.checkbox("Foundit")
            instahala = p7.checkbox("Intershala")
            freshers = p8.checkbox("Freshersworld")
            
            p9, p10, p11, p12 = st.columns(4)
            wellfound = p9.checkbox("Wellfound")
            iimjobs = p10.checkbox("IIMJobs")
            
            submitted = st.form_submit_button("Start Scraping", type="primary")
            
        if submitted:
            active_portals = []
            if naukri: active_portals.append("Naukri")
            if linkedin: active_portals.append("LinkedIn")
            if indeed: active_portals.append("Indeed")
            if glassdoor: active_portals.append("Glassdoor")
            if shine: active_portals.append("Shine")
            if foundit: active_portals.append("Foundit")
            if instahala: active_portals.append("Intershala")
            if freshers: active_portals.append("Freshersworld")
            if wellfound: active_portals.append("Wellfound")
            if iimjobs: active_portals.append("IIMJobs")
            
            st.toast("Scraping started! Please wait...")
            
            with st.status("🔍 Scouting the web for jobs...", expanded=True) as status:
                threads = []
                for p in active_portals:
                    st.write(f"Connecting to {p}...")
                    t = threading.Thread(target=run_scraper, args=(p, keywords, location))
                    t.start()
                    threads.append(t)
                
                # Wait for all to finish
                for t in threads:
                    t.join()
                
                status.update(label="✅ Scraping Complete!", state="complete", expanded=False)
            
            st.success("Scraping finished! Refreshing results...")
            time.sleep(1)
            st.rerun()
                
        st.markdown("---")
        st.subheader("Latest Scraped Jobs")
        
        # INCREASED LIMIT TO 100
        jobs = db.query(Job).order_by(Job.scraped_date.desc()).limit(100).all()
        
        # PROCEED / BULK APPLY BUTTONS
        c1, c2 = st.columns(2)
        if c1.button("✅ Go to Auto-Apply Tab (Matcher)", use_container_width=True):
             st.info("Switch to the 'Auto-Apply' tab in the sidebar to use smart matching!")
             
        if c2.button(f"⚡ Bulk Apply to ALL {len(jobs) if jobs else 0} Jobs", type="primary", use_container_width=True):
            default_resume = db.query(Resume).first()
            if not default_resume:
                st.error("Please upload a resume first in 'Resumes' tab!")
            elif not jobs:
                st.warning("No jobs to apply to.")
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()
                success_count = 0
                applier = AutoApplier()
                try:
                    for i, job in enumerate(jobs):
                        status_text.text(f"Applying to {job.company} ({i+1}/{len(jobs)})...")
                        if applier.apply_to_job(job.id, default_resume.id):
                             success_count += 1
                        progress_bar.progress((i + 1) / len(jobs))
                    
                    st.balloons()
                    st.success(f"Batch Complete! Applied to {success_count} jobs.")
                finally:
                    applier.close_browser()
        
        # INCREASED LIMIT TO 100
        jobs = db.query(Job).order_by(Job.scraped_date.desc()).limit(100).all()
        
        if jobs:
            tab1, tab2 = st.tabs(["Job Cards", "Table View"])
            
            with tab1:
                # Get Default Resume for Quick Apply
                default_resume = db.query(Resume).first()
                
                for job in jobs:
                    st.markdown(f"""
                    <div class="job-card">
                        <div class="job-title">{job.title}</div>
                        <div class="job-company">🏢 {job.company}</div>
                        <div class="job-meta">
                            <div class="job-pill">📍 {job.location}</div>
                            <div class="job-pill">🔗 {job.source}</div>
                            <div class="job-pill">💰 {job.salary}</div>
                            <div class="job-pill">📅 {job.posted_date.strftime('%Y-%m-%d') if job.posted_date else 'Recent'}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    c1, c2 = st.columns([1, 4])
                    if c1.button("⚡ Quick Apply", key=f"quick_apply_{job.id}", type="secondary"):
                        if not default_resume:
                            st.error("Please upload a resume first in 'Resumes' tab!")
                        else:
                            applier = AutoApplier()
                            try:
                                status_placeholder = st.empty()
                                status_placeholder.info(f"Applying to {job.company}...")
                                if applier.apply_to_job(job.id, default_resume.id):
                                    st.toast(f"✅ Applied to {job.company}!")
                                    status_placeholder.success("Applied!")
                                else:
                                    st.toast(f"❌ Failed to apply to {job.company}")
                                    status_placeholder.error("Failed.")
                            finally:
                                applier.close_browser()
                                
                    if c2.button("Link", key=f"link_{job.id}"):
                        st.write(f"URL: {job.url}")
            
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

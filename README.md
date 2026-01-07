# IndianSmartApplier

A complete, local-only job application automation system that runs entirely on your laptop with ZERO cloud costs.

## Features
- **Local Job Scraper**: Scrapes 10 Indian job portals (Naukri, LinkedIn, Indeed, etc.)
- **Resume Parser**: Extracts details from PDF/DOCX resumes.
- **Job Matching Engine**: Uses local AI (spaCy, scikit-learn) to match jobs to your resume.
- **Auto-Apply Agent**: Automates form filling using Selenium.
- **Streamlit Dashboard**: Beautiful local UI for managing the process.
- **Zero External Dependencies**: No API keys, no paid services.

## Setup

1. **Install Dependencies and Models**
   ```bash
   pip install -e .
   python setup.py
   ```

2. **Run the Application**
   ```bash
   streamlit run app.py
   ```

## Usage
1. Open `localhost:8501` in your browser.
2. Upload your resume.
3. Configure job search keywords and location.
4. Start scraping jobs.
5. Review matched jobs and click "Auto-Apply".

## Tech Stack
- Frontend: Streamlit
- Backend: Flask, Selenium, BeautifulSoup
- Database: SQLite
- AI: spaCy, scikit-learn, Transformers

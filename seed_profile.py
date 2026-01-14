import os
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base, AppUser, Resume

# --- DATA ---
RAW_DATA = {
    "name": "SANDEEP KASHYAP",
    "email": "sandeepramaswamykashyap@gmail.com",
    "phone": "+91 6366325217",
    "skills": [
        "UAT Planning & Execution",
        "Process Automation in Recruitment",
        "Requirements Design for AI Products",
        "Client Onboarding & Reference Data",
        "Data Analytics & Insight Generation",
        "AI Agent Workflow Design",
        "Prompt Engineering",
        "Google Anti Gravity",
        "Vibe Coding",
        "Stakeholder Engagement",
        "Agile",
        "Technical Analysis of Stocks & Indices"
    ],
    "experience": [
        {
            "role": "Manager - HR Digital Services",
            "company": "Standard Chartered Global Business Service",
            "years": "February 2019 - Now",
            "description": "Spearheaded AI-driven onboarding process for new employees at SCB, streamlining workflows and enhancing user experience through automation and integration. Designed and implemented HR chatbot and virtual assistant using Jira, resolving employee queries efficiently and reducing support tickets by 78%. Authored detailed change requests, user stories, and technical documentation; collaborated with developers to deliver end-to-end releases using Agile methodologies. Comprehensive requirement gathering sessions conducted with stakeholders to define precise specs for AI and automation projects. Managed full release lifecycle for HR tech initiatives, including requirement gathering, development oversight, testing, and deployment to production environments. Orchestrated end-to-end UAT planning, execution, defect triage, resolution tracking, and stakeholder validation while fostering seamless cross-functional team collaboration to ensure high-quality deliverables and timely project milestones."
        },
        {
            "role": "Team Lead - Client On-Boarding",
            "company": "Wipro Ltd",
            "years": "January 2015 - February 2019",
            "description": "Led reference data management and client onboarding for 500+ UBS clients ensuring regulatory compliance and 99.5% data accuracy across investment banking platforms. Provided SME training and managed BAU escalations improving turnaround time through process automation and operational excellence. Designed executive dashboards streamlined SOPs and implemented controls to close audit gaps and strengthen compliance posture. Drove global product onboarding and maintained 99%+ SLA performance through agile project management and cross-functional collaboration."
        },
        {
            "role": "Business Acquisitions Manager",
            "company": "BBS Pvt Ltd",
            "years": "August 2012 - December 2014",
            "description": "Negotiated and finalised acquisition deals while growing and leveraging business networks. Led client engagements and applied critical thinking to evaluate deal potential and business strategy."
        },
        {
            "role": "Payments Specialist",
            "company": "IBM – Lloyds TSB Bank",
            "years": "August 2010 - June 2012",
            "description": "Processed high-value CHAPS and international payments with a focus on accuracy and compliance. Performed manual payment validation, duplicate checks, sanctions screening, and FX rate capture for multimillion GBP daily volumes."
        }
    ],
    "education": [
        {
            "degree": "Post Graduation - Investment Banking",
            "school": "Indian Institute of Management, India, Indore",
            "year": "2019 - 2020"
        },
        {
            "degree": "Bachelor of Business Management",
            "school": "University of Mysore, India, Hassan",
            "year": "2007 - 2010"
        }
    ],
    "summary": "Extensive Experience: 13+ years in Investment Banking and Technology across top-tier firms (Standard Chartered Bank, Wipro, IBM). AI & Automation Specialist: Expert in deploying AI-driven workflows, prompt engineering, and predictive analytics to modernize operations. Proven Impact: Successfully reduced support tickets by 78% through the implementation of HR chatbots and virtual assistants. Strategic Leadership: Strong background in leading UAT strategies, cross-functional teams, and end-to-end Agile release management. Technical-Business Bridge: Excels at translating business requirements into scalable technical solutions, bridging the gap between developers and stakeholders."
}

# --- DB SETUP ---
DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'sqlite')
DB_PATH = os.path.join(DB_DIR, 'local.db')
engine = create_engine(f"sqlite:///{DB_PATH}")
Session = sessionmaker(bind=engine)
session = Session()

def seed_profile():
    print(f"Connecting to DB at: {DB_PATH}")
    
    # 1. Check User
    email = RAW_DATA["email"]
    user = session.query(AppUser).filter(AppUser.email == email).first()
    
    if user:
        print(f"✅ Found User: {user.name} ({user.email})")
        
        # Update User Name just in case
        if user.name != RAW_DATA["name"]:
            user.name = RAW_DATA["name"]
            print(f"  -> Updated Name to: {RAW_DATA['name']}")
    else:
        print(f"❌ User {email} not found. Creating placeholder user...")
        user = AppUser(
            name=RAW_DATA["name"],
            email=email,
            is_onboarded=True,
            is_admin=True
        )
        user.set_password("admin") # Default safe password
        session.add(user)
        session.commit()
        print(f"✅ Created User: {user.name}")

    # 2. Add Resume Data
    # Check if resume exists
    existing_resume = session.query(Resume).filter(Resume.email == email).first()
    
    if existing_resume:
        print("ℹ️ Updating existing resume...")
        existing_resume.name = RAW_DATA["name"]
        existing_resume.phone = RAW_DATA["phone"]
        existing_resume.parsed_data = RAW_DATA
        existing_resume.raw_text = json.dumps(RAW_DATA, indent=2)
    else:
        print("✨ creating NEW resume...")
        new_resume = Resume(
            name=RAW_DATA["name"],
            email=email,
            phone=RAW_DATA["phone"],
            parsed_data=RAW_DATA,
            raw_text=json.dumps(RAW_DATA, indent=2),
            file_path="manual_entry"
        )
        session.add(new_resume)
    
    session.commit()
    print("✅ Profile & Resume Seeded Successfully!")
    session.close()

if __name__ == "__main__":
    seed_profile()

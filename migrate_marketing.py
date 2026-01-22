
from backend.database import engine, Base, MarketingCampaign, UserCampaignStatus, SessionLocal
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_marketing():
    logger.info("Migrating Marketing Tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Migration Complete.")
    
    # SEED DEFAULT CAMPAIGNS
    db = SessionLocal()
    defaults = [
        {"day": 1, "name": "Day 1: Quick Win", "subject": "🎁 Your first 50 applications are on us", "body": "<p>Welcome! Let's get you hired...</p>"},
        {"day": 3, "name": "Day 3: FOMO", "subject": "📉 You are missing 80% of job matches", "body": "<p>Did you know...</p>"},
        {"day": 7, "name": "Day 7: Social Proof", "subject": "🚀 How Alex got hired in 4 days", "body": "<p>See how...</p>"},
        {"day": 14, "name": "Day 14: The Offer", "subject": "⚡ Unlock Pro: 50% Off for 24 Hours", "body": "<p>Use code START50...</p>"},
        {"day": 30, "name": "Day 30: Re-engagement", "subject": "💔 Is your job search on hold?", "body": "<p>We miss you...</p>"},
    ]
    
    for d in defaults:
        exists = db.query(MarketingCampaign).filter_by(day_offset=d['day']).first()
        if not exists:
            db.add(MarketingCampaign(
                name=d['name'],
                subject=d['subject'],
                body_template=d['body'],
                day_offset=d['day']
            ))
            logger.info(f"Seeded: {d['name']}")
            
    db.commit()
    db.close()

if __name__ == "__main__":
    migrate_marketing()

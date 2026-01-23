import os
import sys
from datetime import datetime

# Add root to python path to allow imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.database import SessionLocal, AppUser, init_db
from backend.utils.logger import logger

def grant_lifetime_access():
    target_email = "ural.rachana@gmail.com"
    target_name = "Rachana Ural HJ"
    
    logger.info(f"🚀 Starting Access Grant for: {target_email}")
    
    db = SessionLocal()
    try:
        user = db.query(AppUser).filter_by(email=target_email).first()
        
        if user:
            logger.info("Found existing user.")
            user.subscription_plan = "PRO_PLUS"
            user.subscription_expiry = datetime(2099, 12, 31)
            user.name = target_name # Update name just in case
            logger.info("✅ Updated Plan to PRO_PLUS (Lifetime)")
        else:
            logger.info("User not found. Creating new account...")
            user = AppUser(
                email=target_email,
                name=target_name,
                password=None, # Will need reset or set manually if not logging in via Google
                is_onboarded=True,
                subscription_plan="PRO_PLUS",
                subscription_expiry=datetime(2099, 12, 31)
            )
            user.set_password("HireLink2026!") # Default temp password
            db.add(user)
            logger.info(f"✅ Created New User with password: HireLink2026!")
            
        db.commit()
        logger.info("💾 Database Changes Saved Successfully.")
        
    except Exception as e:
        logger.error(f"❌ Failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    grant_lifetime_access()

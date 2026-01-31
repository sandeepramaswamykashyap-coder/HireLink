import os
import shutil
from backend.utils.logger import logger

# Import DB_PATH from the source of truth to ensure we match the active application DB
from backend.database import DB_PATH, DB_DIR

# Snapshot will live in the same directory as the database
SNAPSHOT_PATH = os.path.join(DB_DIR, 'admin_snapshot.db')

def save_admin_snapshot():
    """
    Creates a copy of the current local.db as admin_snapshot.db
    """
    try:
        if not os.path.exists(DB_PATH):
            return False, "Database file not found."
            
        # Ensure directory exists just in case
        if not os.path.exists(DB_DIR):
            os.makedirs(DB_DIR)
            
        shutil.copy2(DB_PATH, SNAPSHOT_PATH)
        logger.info(f"Admin snapshot saved to {SNAPSHOT_PATH}")
        return True, "Admin snapshot saved successfully."
    except Exception as e:
        logger.error(f"Failed to save snapshot: {e}")
        return False, str(e)

def restore_admin_snapshot():
    """
    Overwrites local.db with admin_snapshot.db
    """
    try:
        if not os.path.exists(SNAPSHOT_PATH):
            return False, "No saved admin snapshot found."
            
        # Remove current DB first (clean slate) - optional for copy but good practice
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
            
        shutil.copy2(SNAPSHOT_PATH, DB_PATH)
        logger.info(f"Admin snapshot restored from {SNAPSHOT_PATH}")
        return True, "Admin profile restored. Please refresh."
    except Exception as e:
        logger.error(f"Failed to restore snapshot: {e}")
        return False, str(e)

def factory_reset():
    """
    Deletes all data from the database tables to reset app state.
    PREFERRED: SQL Delete over file deletion to avoid file lock issues.
    """
    try:
        from backend.database import SessionLocal, AppUser, Resume, Application, Job, PortalCredential, QuestionAnswer, PortalStatus, Coupon, ReferralTransaction
        
        with SessionLocal() as db:
            # 1. SQL Truncate/Delete
            # Order matters for foreign keys slightly, but sqlite usually lenient unless enforced
            db.query(PortalCredential).delete()
            db.query(QuestionAnswer).delete()
            db.query(Application).delete()
            db.query(Resume).delete()
            db.query(Job).delete()
            db.query(PortalStatus).delete()
            db.query(Coupon).delete()
            db.query(ReferralTransaction).delete()
            db.query(AppUser).delete()
            
            db.commit()
        
        # 2. Try file deletion as bonus (optional)
        if os.path.exists(DB_PATH):
            try:
                os.remove(DB_PATH)
                logger.info("Factory reset: local.db deleted via OS.")
            except:
                logger.warning("Could not delete file, but data was wiped via SQL.")
                
        logger.info("Factory reset: All tables wiped.")
        return True, "App reset to factory settings (Data Wiped)."
    except Exception as e:
        logger.error(f"Failed to factory reset: {e}")
        return False, str(e)

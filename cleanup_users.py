
from backend.database import SessionLocal, AppUser
import sys

def cleanup_users():
    db = SessionLocal()
    target_email = "admin@hirelink.tech"
    
    try:
        # Verify Target Exists First
        target = db.query(AppUser).filter_by(email=target_email).first()
        if not target:
            print(f"❌ Safety Abort! Target user {target_email} not found.")
            return

        print(f"✅ Target User Found: {target.email} (ID: {target.id})")
        
        # Delete Others
        others = db.query(AppUser).filter(AppUser.email != target_email).all()
        count = 0
        for u in others:
            print(f"🗑️ Deleting: {u.email} (ID: {u.id})...")
            # Note: Cascade deletes should handle related data if configured, 
            # otherwise this might leave orphaned records, but that's acceptable for a cleanup.
            db.delete(u)
            count += 1
            
        db.commit()
        print(f"🎉 Cleanup Complete. Deleted {count} users. Preserved {target_email}.")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    cleanup_users()

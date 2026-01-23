import os
import sys
from backend.database import SessionLocal, AppUser

def diagnose():
    print("🔍 DIAGNOSTIC MODE: Listing All Users...")
    try:
        db = SessionLocal()
        users = db.query(AppUser).all()
        
        print(f"{'ID':<5} | {'Email':<30} | {'Plan':<10} | {'Admin?':<6} | {'Expiry'}")
        print("-" * 80)
        
        for u in users:
            print(f"{u.id:<5} | {u.email:<30} | {u.subscription_plan:<10} | {str(u.is_admin):<6} | {u.subscription_expiry}")
            
        print("-" * 80)
        
        # Specific check for Rachana
        target = "ural.rachana@gmail.com"
        u = db.query(AppUser).filter(AppUser.email.ilike(target)).first()
        if u:
            print(f"\n✅ Specific Check for '{target}': MATCH FOUND")
            print(f"   - Stored Email: {u.email}")
            print(f"   - Plan: {u.subscription_plan}")
            print(f"   - Is Admin: {u.is_admin}")
        else:
            print(f"\n❌ Specific Check for '{target}': NOT FOUND")
            
        db.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    diagnose()


from backend.database import SessionLocal, AppUser
import sys

def restore_target_admin():
    db = SessionLocal()
    email = "admin@hirelink.tech"
    target_name = "Sandeep Kashyap"
    
    try:
        user = db.query(AppUser).filter_by(email=email).first()
        
        if user:
            print(f"Found existing user {email}. Updating name...")
            user.name = target_name
            user.is_admin = True # Ensure admin
            db.commit()
            print(f"✅ Updated {email} to Name: {target_name}")
        else:
            print(f"User {email} not found. Creating new...")
            new_user = AppUser(
                name=target_name,
                email=email,
                is_admin=True,
                is_onboarded=True,
                subscription_plan="PRO_PLUS"
            )
            new_user.set_password("admin123")
            db.add(new_user)
            db.commit()
            print(f"✅ Created {email} with Name: {target_name} and Password: 'admin123'")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    restore_target_admin()


from backend.database import SessionLocal, AppUser
import sys

# Ensure we hit the correct DB if not using default
# But SessionLocal should pick up the correct one based on default setup.

def reset_admin_pwd():
    db = SessionLocal()
    target_email = "admin@hirelink.tech"
    new_pwd = "admin123"
    
    try:
        user = db.query(AppUser).filter_by(email=target_email).first()
        if user:
            print(f"User Found: {user.email}")
            user.set_password(new_pwd)
            db.commit()
            print(f"✅ Password RESET to: {new_pwd}")
        else:
            print("❌ User not found!")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    reset_admin_pwd()

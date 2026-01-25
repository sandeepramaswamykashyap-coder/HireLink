
from backend.database import migrate_db, seed_admin, SessionLocal, AppUser

def fix():
    print("running migrations...")
    migrate_db()
    print("seeding admin...")
    seed_admin()
    
    db = SessionLocal()
    u = db.query(AppUser).filter_by(email="admin@hirelink.com").first()
    if u:
        print(f"Verified Admin: {u.email} (ID: {u.id})")
        print("Done.")
    else:
        print("ERROR: Admin not found after seeding.")

if __name__ == "__main__":
    fix()

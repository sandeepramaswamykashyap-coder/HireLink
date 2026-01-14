from backend.database import SessionLocal, AppUser

db = SessionLocal()
users = db.query(AppUser).all()

print(f"Found {len(users)} users in database.")
for u in users:
    print(f"ID: {u.id} | Name: {u.name} | Email: {u.email} | Password: {u.password} | Admin: {getattr(u, 'is_admin', False)}")

db.close()

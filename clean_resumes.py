from backend.database import SessionLocal, Resume, AppUser
sess = SessionLocal()
target_email = "sandeepramaswamykashyap@gmail.com"

# Delete Resumes
deleted_count = sess.query(Resume).filter(Resume.email == target_email).delete()
sess.commit()
print(f"Deleted {deleted_count} resumes for {target_email}")
sess.close()

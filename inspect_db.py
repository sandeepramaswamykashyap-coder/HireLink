from backend.database import SessionLocal, Job

def check_jobs():
    db = SessionLocal()
    try:
        jobs = db.query(Job).filter(Job.source == "Intershala").all()
        print(f"Checking {len(jobs)} Internshala jobs...")
        deleted = 0
        for job in jobs:
            if not job.title or job.title.strip() == "":
                print(f"Deleting invalid job ID {job.id} (URL: {job.url})")
                db.delete(job)
                deleted += 1
        
        if deleted > 0:
            db.commit()
            print(f"Deleted {deleted} invalid jobs.")
        else:
            print("No invalid jobs found.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_jobs()

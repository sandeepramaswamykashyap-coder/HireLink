import sqlite3
import os

target_email = "sandeepramaswamykashyap@gmail.com"
candidates = ["data/sqlite/local.db", "hirelink.db", "data/hirelink.db"]

for db_path in candidates:
    if os.path.exists(db_path):
        print(f"--- Checking {db_path} ---")
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check for table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='resumes'")
            if cursor.fetchone():
                cursor.execute("SELECT count(*) FROM resumes WHERE email=?", (target_email,))
                count = cursor.fetchone()[0]
                print(f"Found {count} resumes.")
                
                if count > 0:
                    cursor.execute("DELETE FROM resumes WHERE email=?", (target_email,))
                    conn.commit()
                    print(f"✅ Deleted {cursor.rowcount} resumes from {db_path}")
            else:
                print(f"Table 'resumes' not found in {db_path}")
            
            conn.close()
        except Exception as e:
            print(f"Error accessing {db_path}: {e}")
    else:
        print(f"Skipped {db_path} (Not Found)")


import os
import sys
# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.utils.notifier import EmailNotifier
from dotenv import load_dotenv

# Load env vars from .env file
load_dotenv()

def test_email():
    print("--- Testing Email Configuration ---")
    notifier = EmailNotifier()
    print(f"SMTP_SERVER: {notifier.smtp_server}")
    print(f"SMTP_PORT: {notifier.smtp_port}")
    print(f"SMTP_USER: {'***' if notifier.username else 'Not Set'}")
    print(f"SMTP_PASSWORD: {'***' if notifier.password else 'Not Set'}")
    print(f"Notifier Enabled: {notifier.enabled}")
    
    if notifier.enabled:
        print("Attempting to send test email to 'notifications@hirelink.tech' (simulated self-send)...")
        # In real scenario we'd send to the user, but let's try sending to the SMTP user itself if possible, 
        # or just a placeholder to see if it connects.
        try:
            success = notifier.send_digest(to_email=notifier.username, new_jobs_count=5, top_job_title="Test Job")
            if success:
                print("✅ Email Sent Successfully!")
            else:
                print("❌ Email Failed (returned False)")
        except Exception as e:
            print(f"❌ Email Failed with Exception: {e}")
    else:
        print("⚠️ Email system is DISABLED because credentials are missing.")

if __name__ == "__main__":
    test_email()

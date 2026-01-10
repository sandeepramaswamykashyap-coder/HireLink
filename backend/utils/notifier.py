
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from backend.utils.logger import logger

class EmailNotifier:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.username = os.getenv("SMTP_USER")
        self.password = os.getenv("SMTP_PASSWORD")
        self.enabled = bool(self.username and self.password)

    def send_digest(self, to_email, new_jobs_count, top_job_title=None):
        """
        Sends a summary email of the latest automation run.
        """
        if not self.enabled:
            logger.warning("EmailNotifier: SMTP credentials not set. Skipping email.")
            return False
            
        try:
            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['To'] = to_email
            msg['Subject'] = f"🚀 HireLink Report: Found {new_jobs_count} New Jobs"

            body = f"""
            <h2>HireLink Daily Digest</h2>
            <p>Your AI Agent has been hard at work.</p>
            <ul>
                <li><strong>New Jobs Scraped:</strong> {new_jobs_count}</li>
                <li><strong>Top Opportunity:</strong> {top_job_title or 'N/A'}</li>
            </ul>
            <p>Log in to your dashboard to view full details and apply.</p>
            <br>
            <p><em>- The HireLink Bot</em></p>
            """
            
            msg.attach(MIMEText(body, 'html'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.username, self.password)
            text = msg.as_string()
            server.sendmail(self.username, to_email, text)
            server.quit()
            
            logger.info(f"Email digest sent to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

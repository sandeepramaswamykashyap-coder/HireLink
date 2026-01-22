
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
    def send_session_report(self, to_email, session_data):
        """
        Sends a detailed session report with a table of actions.
        session_data = {
            'total': int,
            'success': int,
            'logs': [{'title': str, 'company': str, 'status': str, 'portal': str}]
        }
        """
        if not self.enabled:
            logger.warning("EmailNotifier: SMTP credentials not set. Skipping report.")
            return False
            
        try:
            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['To'] = to_email
            msg['Subject'] = f"📊 Session Report: {session_data['success']} Applications Sent"

            # Build Table Rows
            rows = ""
            for log in session_data.get('logs', []):
                color = "#d1fae5" if log['status'] == "Success" else "#fee2e2"
                text_color = "#065f46" if log['status'] == "Success" else "#991b1b"
                rows += f"""
                <tr style="border-bottom: 1px solid #e5e7eb;">
                    <td style="padding: 12px;">{log['title']}</td>
                    <td style="padding: 12px;">{log['company']}</td>
                    <td style="padding: 12px;">{log.get('portal', 'N/A')}</td>
                    <td style="padding: 12px;"><span style="background-color: {color}; color: {text_color}; padding: 4px 8px; border-radius: 9999px; font-size: 12px; font-weight: bold;">{log['status']}</span></td>
                </tr>
                """

            body = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #1e3a8a;">Job Pilot Session Report</h2>
                <p>Here is the summary of your recent autonomous application session.</p>
                
                <div style="display: flex; gap: 20px; margin-bottom: 20px;">
                    <div style="background: #f3f4f6; padding: 15px; border-radius: 8px;">
                        <span style="display: block; font-size: 12px; color: #6b7280; font-weight: bold;">TOTAL PROCESSED</span>
                        <span style="font-size: 24px; font-weight: bold; color: #111827;">{session_data['total']}</span>
                    </div>
                    <div style="background: #ecfdf5; padding: 15px; border-radius: 8px;">
                        <span style="display: block; font-size: 12px; color: #065f46; font-weight: bold;">SUCCESSFUL</span>
                        <span style="font-size: 24px; font-weight: bold; color: #059669;">{session_data['success']}</span>
                    </div>
                </div>

                <table style="width: 100%; border-collapse: collapse; font-size: 14px; text-align: left;">
                    <thead>
                        <tr style="background-color: #f9fafb; border-bottom: 2px solid #e5e7eb;">
                            <th style="padding: 12px;">Role</th>
                            <th style="padding: 12px;">Company</th>
                            <th style="padding: 12px;">Portal</th>
                            <th style="padding: 12px;">Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows}
                    </tbody>
                </table>
                <br>
                <p><em>Keep aiming high! 🚀</em></p>
                <p style="font-size: 12px; color: #9ca3af;">HireLink Tech Pvt. Ltd.</p>
            </div>
            """
            
            msg.attach(MIMEText(body, 'html'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.username, self.password)
            text = msg.as_string()
            server.sendmail(self.username, to_email, text)
            server.quit()
            
            logger.info(f"Session report sent to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send session report: {e}")
            return False

    def send_password_reset(self, to_email, reset_link):
        """
        Sends a password reset link to the user.
        """
        if not self.enabled:
            logger.warning("EmailNotifier: SMTP credentials not set. Skipping reset email.")
            return False
            
        try:
            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['To'] = to_email
            msg['Subject'] = "🔐 Reset Your HireLink Password"

            body = f"""
            <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto; color: #333;">
                <h2 style="color: #1e3a8a;">Password Reset Request</h2>
                <p>We received a request to reset your password for HireLink.</p>
                <p>Click the button below to set a new password:</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_link}" style="background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">Reset Password</a>
                </div>
                
                <p style="font-size: 13px; color: #666;">Or copy this link:<br><a href="{reset_link}">{reset_link}</a></p>
                
                <p style="font-size: 13px; color: #999;">If you didn't ask for this, you can ignore this email. This link expires in 15 minutes.</p>
            </div>
            """
            
            msg.attach(MIMEText(body, 'html'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.username, self.password)
            text = msg.as_string()
            server.sendmail(self.username, to_email, text)
            server.quit()
            
            logger.info(f"Password reset email sent to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send reset email: {e}")
            return False

    def send_email(self, to_email, subject, html_body, sender_override=None):
        """
        Generic method to send any HTML email.
        """
        if not self.enabled:
            logger.warning("EmailNotifier: SMTP credentials not set. Skipping generic email.")
            return False
            
        try:
            msg = MIMEMultipart()
            msg['From'] = sender_override if sender_override else self.username
            msg['To'] = to_email
            msg['Subject'] = subject

            msg.attach(MIMEText(html_body, 'html'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.username, self.password)
            text = msg.as_string()
            server.sendmail(self.username, to_email, text)
            server.quit()
            
            logger.info(f"Generic email sent to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send generic email: {e}")
            return False


from backend.database import SessionLocal, AppUser, MarketingCampaign, UserCampaignStatus
from backend.utils.notifier import EmailNotifier, logger
from datetime import datetime
import logging

class MarketingEngine:
    def __init__(self):
        self.db = SessionLocal()
        self.notifier = EmailNotifier()
        
    def get_campaign_status(self):
        """Return stats for UI"""
        total_campaigns = self.db.query(MarketingCampaign).count()
        emails_sent = self.db.query(UserCampaignStatus).count()
        return {"active_campaigns": total_campaigns, "emails_delivered": emails_sent}

    def run_daily_campaign(self, dry_run=False):
        """
        Main logic to find eligible users and send expected emails.
        Returns a log of actions.
        """
        log = []
        try:
            # 1. Get Target Users (All valid users)
            # Filter: NOT Paid users (optionally? For now, let's target FREE/TRIAL)
            users = self.db.query(AppUser).filter(AppUser.subscription_plan.in_(['FREE', 'TRIAL'])).all()
            campaigns = self.db.query(MarketingCampaign).all()
            
            sender = "HireLink Notifications <notifications@hirelink.tech>"

            for user in users:
                # Calculate User Age in Days
                days_active = (datetime.utcnow() - user.created_at).days
                
                for camp in campaigns:
                    # Logic: If user age matches campaign offset (+/- coverage?)
                    # Let's say: If user day >= camp.day AND not sent yet.
                    if days_active >= camp.day_offset:
                        # Check if already sent
                        sent = self.db.query(UserCampaignStatus).filter_by(user_id=user.id, campaign_id=camp.id).first()
                        if not sent:
                            # SEND IT
                            if not dry_run:
                                success = self.notifier.send_email(
                                    to_email=user.email,
                                    subject=camp.subject,
                                    html_body=camp.body_template,
                                    sender_override=sender
                                )
                                if success:
                                    # Record
                                    record = UserCampaignStatus(user_id=user.id, campaign_id=camp.id, status="Sent")
                                    self.db.add(record)
                                    self.db.commit()
                                    log.append(f"✅ Sent '{camp.name}' to {user.email}")
                                else:
                                    log.append(f"❌ Failed to send to {user.email} (SMTP Error)")
                            else:
                                log.append(f"ℹ️ [DRY RUN] Would send '{camp.name}' to {user.email}")
        except Exception as e:
            log.append(f"🔥 Critical Error: {str(e)}")
            logger.error(f"Marketing Engine Error: {e}")
        finally:
            self.db.close()
            
        return log

    def generate_copy_with_ai(self, prompt, context):
        """
        Placeholder for LLM generation.
        """
        # In a real scenario, this calls Google Gemini via `backend.utils.llm_helper`
        # For now, return a mock or simple implementation
        return f"AI Generated Content for: {prompt}"

if __name__ == "__main__":
    eng = MarketingEngine()
    print(eng.run_daily_campaign(dry_run=True))


from backend.database import SessionLocal, AppUser, Coupon
from backend.utils.notifier import EmailNotifier
import logging
from dotenv import load_dotenv

# Load Env
load_dotenv()

# Configure Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_campaign():
    db = SessionLocal()
    try:
        # 1. Ensure Coupon Exists
        coupon_code = "SAVE90-JL3P"
        discount = 90
        
        existing_coupon = db.query(Coupon).filter_by(code=coupon_code).first()
        if not existing_coupon:
            logger.info(f"Creating new coupon: {coupon_code} ({discount}%)")
            new_coupon = Coupon(code=coupon_code, discount_percent=discount)
            db.add(new_coupon)
            db.commit()
        else:
            logger.info(f"Coupon {coupon_code} already exists.")

        # 2. Get Users
        users = db.query(AppUser).all()
        logger.info(f"Found {len(users)} users to convert.")
        
        notifier = EmailNotifier()
        
        # 3. Send Emails
        subject = "🚀 Exclusive: 90% OFF HireLink Pro (Limited Time)"
        
        for u in users:
            logger.info(f"Sending to {u.email}...")
            
            # HTML Template
            body = f"""
            <div style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;">
                <div style="background-color: #0f172a; padding: 20px; text-align: center;">
                    <h1 style="color: #ffffff; margin: 0;">⚡ Flash Sale Alert</h1>
                </div>
                <div style="padding: 30px;">
                    <p>Hi {u.name},</p>
                    <p>We are unlocking our biggest discount ever to help you land your dream job faster.</p>
                    
                    <div style="background-color: #f0fdf4; border: 1px dashed #22c55e; padding: 20px; text-align: center; margin: 25px 0; border-radius: 8px;">
                        <span style="display: block; font-size: 14px; color: #15803d; margin-bottom: 5px;">USE CODE:</span>
                        <span style="font-size: 32px; font-weight: bold; color: #166534; letter-spacing: 2px;">{coupon_code}</span>
                        <span style="display: block; font-size: 18px; color: #dc2626; font-weight: bold; margin-top: 10px;">Get 90% OFF PRO Plans</span>
                    </div>
                    
                    <p><strong>This unlocks:</strong></p>
                    <ul>
                        <li>✨ Unlimited AI Resume Builds</li>
                        <li>🤖 Auto-Apply to 500+ Jobs/day</li>
                        <li>📧 Priority Email Support</li>
                    </ul>
                    
                    <div style="text-align: center; margin-top: 30px;">
                        <a href="https://hirelink.tech" style="background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">Claim Offer Now</a>
                    </div>
                </div>
                <div style="background-color: #f8fafc; padding: 15px; text-align: center; font-size: 12px; color: #64748b;">
                    <p>Offer valid for next 24 hours. Hurry!</p>
                </div>
            </div>
            """
            
            # Send
            try:
                if notifier.send_email(u.email, subject, body):
                    logger.info(f"✅ Sent to {u.email}")
                else:
                    logger.error(f"❌ Failed (SMTP Error) for {u.email}")
            except Exception as e:
                logger.error(f"❌ Failed to send to {u.email}: {e}")
                
    except Exception as e:
        logger.error(f"Campaign Failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_campaign()

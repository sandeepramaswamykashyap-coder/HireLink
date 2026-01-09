import random
import string
from backend.database import SessionLocal, AppUser, ReferralTransaction
from backend.utils.logger import logger
from datetime import datetime

class AffiliateManager:
    @staticmethod
    def generate_unique_code(name):
        """Generates a clean, readable referral code from a name."""
        prefix = ''.join(e for e in name if e.isalnum()).upper()[:6]
        suffix = ''.join(random.choices(string.digits, k=3))
        code = f"{prefix}{suffix}"
        
        # Check uniqueness in DB
        db = SessionLocal()
        try:
            while db.query(AppUser).filter(AppUser.referral_code == code).first():
                suffix = ''.join(random.choices(string.digits, k=3))
                code = f"{prefix}{suffix}"
            return code
        finally:
            db.close()

    @staticmethod
    def apply_referral(user_id, referral_code):
        """Links a new user to their referrer using a code."""
        db = SessionLocal()
        try:
            referrer = db.query(AppUser).filter(AppUser.referral_code == referral_code).first()
            if not referrer:
                return False
            
            user = db.query(AppUser).get(user_id)
            if user and not user.referred_by_id:
                user.referred_by_id = referrer.id
                referrer.referral_count += 1
                db.commit()
                logger.info(f"User {user_id} attributed to Referrer {referrer.id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error applying referral: {e}")
            return False
        finally:
            db.close()

    @staticmethod
    def process_commission(referee_id, amount_paid):
        """Calculates and credits commission to the referrer when referee pays."""
        db = SessionLocal()
        try:
            referee = db.query(AppUser).get(referee_id)
            if not referee or not referee.referred_by_id:
                return
            
            referrer = db.query(AppUser).get(referee.referred_by_id)
            if not referrer:
                return

            # Flat Reward Logic (No Payouts, Only Discount Credits)
            credit_amount = 500.0 # ₹500 discount for the referrer
            
            # 1. Update Referrer Credits
            referrer.earnings_balance += credit_amount
            
            # 2. Log Transaction
            log = ReferralTransaction(
                referrer_id=referrer.id,
                referee_id=referee.id,
                amount=credit_amount,
                transaction_type="SERVICE_CREDIT",
                status="COMPLETED" # Applied immediately
            )
            db.add(log)
            db.commit()
            logger.info(f"Service Credit of {credit_amount} added to user {referrer.id}")
            
        except Exception as e:
            logger.error(f"Error processing commission: {e}")
        finally:
            db.close()

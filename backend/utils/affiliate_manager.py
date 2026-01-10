import random
import string
from backend.database import SessionLocal, AppUser, ReferralTransaction
from backend.utils.logger import logger
from datetime import datetime

class AffiliateManager:
    @staticmethod
    def generate_unique_code(name, db=None):
        """Generates a clean, readable referral code from a name."""
        prefix = ''.join(e for e in name if e.isalnum()).upper()[:6]
        suffix = ''.join(random.choices(string.digits, k=3))
        code = f"{prefix}{suffix}"
        
        # Check uniqueness in DB
        _db = db if db else SessionLocal()
        try:
            while _db.query(AppUser).filter(AppUser.referral_code == code).first():
                suffix = ''.join(random.choices(string.digits, k=3))
                code = f"{prefix}{suffix}"
            return code
        finally:
            if not db: _db.close()

    @staticmethod
    def apply_referral(user_id, referral_code, db=None):
        """Links a new user to their referrer using a code."""
        _db = db if db else SessionLocal()
        try:
            referrer = _db.query(AppUser).filter(AppUser.referral_code == referral_code).first()
            if not referrer:
                return False
            
            user = _db.query(AppUser).get(user_id)
            if user and not user.referred_by_id:
                user.referred_by_id = referrer.id
                referrer.referral_count += 1
                _db.commit()
                logger.info(f"User {user_id} attributed to Referrer {referrer.id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error applying referral: {e}")
            return False
        finally:
            if not db: _db.close()

    @staticmethod
    def process_commission(referee_id, amount_paid, db=None):
        """Calculates and credits commission to the referrer when referee pays."""
        _db = db if db else SessionLocal()
        try:
            referee = _db.query(AppUser).get(referee_id)
            if not referee or not referee.referred_by_id:
                return
            
            referrer = _db.query(AppUser).get(referee.referred_by_id)
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
            _db.add(log)
            _db.commit()
            logger.info(f"Service Credit of {credit_amount} added to user {referrer.id}")
            
        except Exception as e:
            logger.error(f"Error processing commission: {e}")
        finally:
            if not db: _db.close()

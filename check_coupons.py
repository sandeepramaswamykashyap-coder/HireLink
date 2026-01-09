
from backend.database import SessionLocal, Coupon
db = SessionLocal()
try:
    coupons = db.query(Coupon).all()
    print("Available Coupons:")
    for c in coupons:
        print(f"Code: '{c.code}', Discount: {c.discount_percent}%, Active: {c.is_active}")
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()

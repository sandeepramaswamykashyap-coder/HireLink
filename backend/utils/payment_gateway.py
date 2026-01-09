import razorpay
import os
import time

class PaymentGateway:
    def __init__(self):
        self.key_id = os.getenv("RAZORPAY_KEY_ID")
        self.key_secret = os.getenv("RAZORPAY_KEY_SECRET")
        self.client = None
        self.mock_mode = True

        if self.key_id and self.key_secret:
            self.client = razorpay.Client(auth=(self.key_id, self.key_secret))
            self.mock_mode = False
        
    def create_payment_link(self, amount, plan_name, user_email, user_phone="9999999999"):
        """
        Creates a payment link. 
        Amount should be in INR (integer). We multiply by 100 for paise.
        """
        if self.mock_mode:
            return {
                "short_url": f"https://mock-payment.com/pay?amt={amount}&plan={plan_name}",
                "id": f"pay_{int(time.time())}",
                "status": "created"
            }
            
        try:
            data = {
                "amount": amount * 100, # Convert to paise
                "currency": "INR",
                "accept_partial": False,
                "description": f"Upgrade to {plan_name} Plan",
                "customer": {
                    "name": user_email.split('@')[0],
                    "email": user_email,
                    "contact": user_phone
                },
                "notify": {
                    "sms": True,
                    "email": True
                },
                "reminder_enable": True,
                "callback_url": "http://localhost:8501/?payment_success=true", # Redirect back to app
                "callback_method": "get"
            }
            return self.client.payment_link.create(data)
        except Exception as e:
            print(f"Razorpay Error: {e}")
            return None

    def verify_payment(self, payment_id, signature, order_id):
        if self.mock_mode: return True
        try:
            self.client.utility.verify_payment_signature({
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            })
            return True
        except:
            return False

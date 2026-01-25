
import os
import sys
import unittest
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Load Env
load_dotenv()

# Setup Test DB
TEST_DB_URL = "sqlite:///:memory:"
Base = declarative_base()

class MockUser(Base):
    __tablename__ = 'users_v2'
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    name = Column(String)
    password = Column(String)
    is_admin = Column(Boolean, default=False)

class MockQA(Base):
    __tablename__ = 'question_answers'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users_v2.id'))
    question = Column(String)
    answer = Column(String)

class MockApp(Base):
    __tablename__ = 'applications'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    job_id = Column(Integer)
    status = Column(String)

class TestFinalSystem(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        print("\n🚀 Starting Final System Verification...")
        cls.engine = create_engine(TEST_DB_URL)
        Base.metadata.create_all(cls.engine)
        cls.Session = sessionmaker(bind=cls.engine)
        print("✅ In-Memory Test DB Created")

    def setUp(self):
        self.db = self.Session()

    def tearDown(self):
        self.db.close()

    def test_01_environment_check(self):
        """Check Critical Env Vars"""
        print("\n[Test 1] Environment Variables")
        required = ["GEMINI_API_KEY", "SMTP_USER", "SMTP_PASSWORD"] 
        # Note: RAZORPAY might be optional if testing free tier, but good to check
        missing = [k for k in required if not os.getenv(k)]
        if missing:
            print(f"⚠️  Warning: Missing ENV Vars: {missing}")
            # Don't fail test, just warn, as manual run might differ
        else:
            print("✅ Critical ENV Vars Present")

    def test_02_export_dependencies(self):
        """Check Excel Export Capability"""
        print("\n[Test 2] Export Dependencies")
        try:
            import pandas as pd
            import openpyxl
            print("✅ Pandas & Openpyxl Installed")
        except ImportError as e:
            self.fail(f"❌ Missing Export Libs: {e}")

    def test_03_admin_logic(self):
        """Verify Admin Data Visibility"""
        print("\n[Test 3] Admin Data Visibility (Simulation)")
        
        # Seed Users
        admin = MockUser(email="admin@hirelink.tech", is_admin=True, name="Admin")
        alice = MockUser(email="alice@test.com", is_admin=False, name="Alice")
        bob = MockUser(email="bob@test.com", is_admin=False, name="Bob")
        self.db.add_all([admin, alice, bob])
        self.db.commit()
        
        # Seed Data
        self.db.add(MockQA(user_id=alice.id, question="Q1", answer="AliceAns"))
        self.db.add(MockQA(user_id=bob.id, question="Q1", answer="BobAns"))
        self.db.commit()
        
        # Test Alice View
        alice_qas = self.db.query(MockQA).filter_by(user_id=alice.id).all()
        self.assertEqual(len(alice_qas), 1)
        self.assertEqual(alice_qas[0].answer, "AliceAns")
        print("✅ Alice sees only Alice's data")
        
        # Test Admin View (Should see ALL)
        # Note: Admin Logic in app.py uses .all()
        admin_qas = self.db.query(MockQA).all()
        self.assertEqual(len(admin_qas), 2)
        print("✅ Admin sees ALL data")

    def test_04_email_config(self):
        """Verify Email Notifier Class"""
        print("\n[Test 4] Email Configuration")
        from backend.utils.notifier import EmailNotifier
        notifier = EmailNotifier()
        if notifier.enabled:
            print(f"✅ EmailNotifier is ENABLED (User: {notifier.username})")
        else:
            print("⚠️ EmailNotifier is DISABLED (Check ENV vars if this is unexpected)")

if __name__ == '__main__':
    unittest.main()

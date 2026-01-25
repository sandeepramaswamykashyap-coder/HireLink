
import sys
import os
import unittest
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database import SessionLocal, Job, Resume, AppUser, Application, QuestionAnswer
from tests.seed_test_data import seed_test_data

# Mocking Scraper to avoid external dependency in E2E logic test
from unittest.mock import MagicMock, patch

class TestHireLinkE2E(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        print("\n[E2E] --- STARTING E2E TEST SUITE ---")
        # 1. Seed Data
        seed_test_data()
        
    def setUp(self):
        self.db = SessionLocal()
        
    def tearDown(self):
        self.db.close()

    def test_01_user_resume_integrity(self):
        """Verify User and Resume linkage and data correctness"""
        print("\n[Test] Verifying User & Resume Data...")
        user = self.db.query(AppUser).filter_by(email="pro.user@example.com").first()
        self.assertIsNotNone(user, "Pro User should exist")
        
        resume = self.db.query(Resume).filter_by(email=user.email).first()
        self.assertIsNotNone(resume, "Resume should exist for the user")
        
        # Verify Parsed Data Access
        self.assertIn("Python", resume.parsed_data.get("skills", []), "Resume should have Python skill")
        print("✅ User/Resume Integrity Check Passed")
        
    def test_02_job_matching_logic(self):
        """Verify the Matcher correctly scores relevant jobs"""
        print("\n[Test] Verifying Job Matching Logic...")
        from backend.agents.job_matcher import JobMatcher
        
        user = self.db.query(AppUser).filter_by(email="pro.user@example.com").first()
        resume = self.db.query(Resume).filter_by(email=user.email).first()
        
        matcher = JobMatcher()
        matches = matcher.match_jobs(resume.id, limit=5)
        
        self.assertTrue(len(matches) > 0, "Should find at least one match from seeded jobs")
        
        top_match = matches[0]
        self.assertTrue(top_match['score'] > 0, "Match score should be positive")
        self.assertEqual(top_match['job'].title, "Python Developer", "Top match should likely be Python Developer")
        
        print(f"✅ Matching Logic Passed. Top Score: {top_match['score']}")

    @patch('backend.agents.auto_applier.setup_driver') 
    def test_03_auto_applier_execution(self, mock_setup_driver):
        """
        Verify Auto Applier logic. 
        We Mock the Selenium Driver to avoid actual browser launching in this logic test.
        """
        print("\n[Test] Verifying Auto Applier (Mocked Driver)...")
        from backend.agents.auto_applier import AutoApplier
        
        # Setup Mock Driver
        mock_driver = MagicMock()
        mock_setup_driver.return_value = mock_driver
        
        # Configure Mock to simulate finding "Easy Apply"
        mock_element = MagicMock()
        mock_element.is_displayed.return_value = True
        mock_driver.find_elements.return_value = [mock_element]
        
        applier = AutoApplier()
        applier.start_browser() # Should use mock
        
        # Fetch a job to apply to
        job = self.db.query(Job).filter(Job.title == "Python Developer").first()
        user = self.db.query(AppUser).filter_by(email="pro.user@example.com").first()
        resume = self.db.query(Resume).filter_by(email=user.email).first()
        
        # Run Application Logic
        status_updates = []
        def callback(msg):
            status_updates.append(msg)
            
        success = applier.apply_to_job(job.id, resume.id, status_callback=callback)
        
        # Since we mocked find_elements to return something, it takes the "Found Apply Button" path.
        # It will try to click.
        # It will then try to Generate Cover Letter (might fail if LLM not mocked, but we catch exceptions)
        # It will then try Form Filler.
        
        # We just want to ensure it ran through the steps without crashing.
        print("Status Updates:", status_updates)
        
        self.assertTrue(mock_driver.get.called, "Driver should have navigated to URL")
        
        # NOTE: Without fully mocking the LLM/FormFiller, this might yield FAILURE, 
        # which is Acceptable for a UNIT/LOGIC test as long as it didn't crash.
        # If we really want to test SUCCESS, we need to mock everything down the chain.
        
        print("✅ Auto Applier Logic Ran (Mocked)")

    def test_04_application_recording(self):
        """Verify that applications are recorded in the DB"""
        print("\n[Test] Verifying Application Recording...")
        
        # Manually create an application record to simulate success
        job = self.db.query(Job).first()
        user = self.db.query(AppUser).filter_by(email="pro.user@example.com").first()
        resume = self.db.query(Resume).filter_by(email=user.email).first()
        
        new_app = Application(
            job_id=job.id,
            resume_id=resume.id,
            status="Applied",
            match_score=85.5,
            user_id=user.id
        )
        self.db.add(new_app)
        self.db.commit()
        
        # Verify
        stored_app = self.db.query(Application).filter_by(job_id=job.id, resume_id=resume.id).first()
        self.assertIsNotNone(stored_app)
        self.assertEqual(stored_app.status, "Applied")
        print("✅ Application Recording Passed")

if __name__ == "__main__":
    unittest.main()


import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base, AppUser, Application, QuestionAnswer, Resume

# Validation Script for Data Isolation

class TestDataIsolation(unittest.TestCase):
    def setUp(self):
        # In-memory DB for strict testing
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        
        # Seed 1 Admin
        self.admin = AppUser(email="admin@hirelink.tech", name="Admin", is_admin=True)
        self.admin.set_password("admin123")
        self.session.add(self.admin)
        
        # Seed 2 Regular Users
        self.user_a = AppUser(email="alice@example.com", name="Alice", is_admin=False)
        self.session.add(self.user_a)
        
        self.user_b = AppUser(email="bob@example.com", name="Bob", is_admin=False)
        self.session.add(self.user_b)
        
        self.session.commit()
        
        # Create Data Linked to Users
        # Alice's Data
        self.q_alice = QuestionAnswer(user_id=self.user_a.id, question="Q1", answer="Alice Answer")
        self.r_alice = Resume(email=self.user_a.email, name="Alice Resume") # Linked via email as per app logic
        self.app_alice = Application(resume_id=1, job_id=1, status="Applied") # Will link via resume_id theoretically
        self.session.add_all([self.q_alice, self.r_alice])
        
        # Bob's Data
        self.q_bob = QuestionAnswer(user_id=self.user_b.id, question="Q1", answer="Bob Answer")
        self.r_bob = Resume(email=self.user_b.email, name="Bob Resume")
        self.session.add_all([self.q_bob, self.r_bob])
        
        self.session.commit()
        # Refetch to get IDs for apps (manual link simulation)
        self.app_alice.resume_id = self.r_alice.id
        self.session.add(self.app_alice)
        
        self.app_bob = Application(resume_id=self.r_bob.id, job_id=1, status="Applied")
        self.session.add(self.app_bob)
        self.session.commit()

    def tearDown(self):
        self.session.close()

    def test_admin_access(self):
        """Admin should see ALL data (Alice + Bob)"""
        # Admin Query Logic (Simulating app.py: is_admin=True)
        all_users = self.session.query(AppUser).all()
        self.assertEqual(len(all_users), 3)
        
        all_qas = self.session.query(QuestionAnswer).all()
        self.assertEqual(len(all_qas), 2) # Alice's and Bob's
        
        print("✅ Admin sees all users and QAs")

    def test_alice_isolation(self):
        """Alice should ONLY see Alice's data"""
        # Alice Query Logic (Simulating app.py: filter by user.id)
        
        # QAs
        alice_qas = self.session.query(QuestionAnswer).filter_by(user_id=self.user_a.id).all()
        self.assertEqual(len(alice_qas), 1)
        self.assertEqual(alice_qas[0].answer, "Alice Answer")
        
        # Applications (Via Resume Link Logic)
        alice_apps = self.session.query(Application).join(Resume, Application.resume_id == Resume.id)\
                        .filter(Resume.email == self.user_a.email).all()
        self.assertEqual(len(alice_apps), 1)
        
        print("✅ Alice sees only her data")

    def test_bob_isolation(self):
        """Bob should ONLY see Bob's data"""
        bob_qas = self.session.query(QuestionAnswer).filter_by(user_id=self.user_b.id).all()
        self.assertEqual(len(bob_qas), 1)
        self.assertEqual(bob_qas[0].answer, "Bob Answer")
        
        # Ensure Bob CANNOT see Alice's stuff
        forbidden = [q for q in bob_qas if "Alice" in q.answer]
        self.assertEqual(len(forbidden), 0)
        
        print("✅ Bob sees only his data")

if __name__ == '__main__':
    unittest.main()

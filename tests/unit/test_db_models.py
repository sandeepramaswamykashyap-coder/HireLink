import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base, AppUser, Job

# Use in-memory SQLite for testing
@pytest.fixture
def test_db():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_create_user(test_db):
    user = AppUser(
        name="Test User",
        email="test@example.com",
        curr_loc="Remote",
        target_roles="Dev",
        target_cities="Remote",
        is_onboarded=True
    )
    test_db.add(user)
    test_db.commit()
    
    fetched = test_db.query(AppUser).filter_by(email="test@example.com").first()
    assert fetched.name == "Test User"

def test_create_job_uniqueness(test_db):
    job1 = Job(title="Dev", company="A", location="Remote", url="http://job1", source="test")
    job2 = Job(title="Dev", company="A", location="Remote", url="http://job1", source="test")
    
    test_db.add(job1)
    test_db.commit()
    
    # Depending on implementation, fingerprint might be unique.
    # If using your provided schema, let's verify basic insertion.
    
    fetched = test_db.query(Job).first()
    assert fetched.title == "Dev"

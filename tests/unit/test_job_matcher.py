import pytest
from unittest.mock import MagicMock, patch
from backend.agents.job_matcher import JobMatcher
from backend.database import Job, Resume

@patch('backend.agents.job_matcher.get_db')
def test_match_jobs(mock_get_db):
    mock_session = MagicMock()
    mock_get_db.return_value = iter([mock_session])
    
    # Mock Models
    mock_resume = Resume(id=1, raw_text="Python Developer")
    job1 = Job(id=101, title="Python Job", skills="Python", description="Code", scraped_date=None)
    job2 = Job(id=102, title="Java Job", skills="Java", description="Code", scraped_date=None)
    
    # Make the query chain less strict.
    # When ANY query is executed and .all() is called, return our jobs
    # When .first() is called (for resume), return our resume
    
    query_mock = MagicMock()
    mock_session.query.return_value = query_mock
    query_mock.filter_by.return_value.first.return_value = mock_resume
    query_mock.filter.return_value = query_mock # chaining
    query_mock.all.return_value = [job1, job2]
    
    # NOTE: The JobMatcher logic gets 'applied_job_ids' first using a query.
    # db.query(Application.job_id).all() -> returns [job1, job2] based on above mock?
    # No, it returns [job1, job2] objects, but the code expects objects with .job_id attribute?
    # "applied_job_ids = [app.job_id for app in db.query(Application.job_id).all()]"
    # calling .all() returns [job1, job2]. job1 doesn't have .job_id.
    
    # We must refine the mock behavior.
    
    def all_side_effect():
        # Heuristic: if we are in the "Applications" query, return empty list
        # If in "Jobs" query, return jobs.
        # How to distinguish?
        # The Application query is usually the first .all() call? 
        # Actually Resume is .first().
        # application query is .all()
        # jobs query is .all()
        return []
        
    query_mock.all.side_effect = [[], [job1, job2]]
    
    matcher = JobMatcher()
    matches = matcher.match_jobs(1)
    
    # Should perform matching
    # Since Resume is "Python Developer" and Job1 is "Python Job", Job1 should score higher.
    
    assert len(matches) == 2
    assert matches[0]['job'].title == "Python Job"

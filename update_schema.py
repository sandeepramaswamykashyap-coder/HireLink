
from backend.database import engine, Base, ActivityLog
import logging

# Configure Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_schema():
    logger.info("Checking for missing tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Schema Updated! 'activity_logs' should now exist.")

if __name__ == "__main__":
    update_schema()

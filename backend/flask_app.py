from flask import Flask, jsonify, request
from backend.database import init_db, get_db, Job
from backend.utils.logger import logger
import threading

app = Flask(__name__)

# Initialize DB on startup
with app.app_context():
    init_db()

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "service": "HireLink-Backend"})

@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    db = next(get_db())
    jobs = db.query(Job).limit(100).all()
    return jsonify([{
        "id": job.id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "source": job.source,
        "url": job.url
    } for job in jobs])

def run_flask():
    logger.info("Starting Flask server on port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

if __name__ == "__main__":
    run_flask()

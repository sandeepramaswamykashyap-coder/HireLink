import scrapy
from backend.database import SessionLocal, Job
from datetime import datetime

class PortalSpider(scrapy.Spider):
    name = "portal_spider"
    
    def __init__(self, keywords=None, location=None, *args, **kwargs):
        super(PortalSpider, self).__init__(*args, **kwargs)
        self.keywords = keywords
        self.location = location
        # Example URL logic
        self.start_urls = [f"https://www.example-job-portal.com/search?q={keywords}&l={location}"]

    def parse(self, response):
        """
        Scrapy's high-speed parsing logic.
        """
        for job_card in response.css('.job-card'):
            title = job_card.css('.title::text').get()
            company = job_card.css('.company::text').get()
            link = job_card.css('a::attr(href)').get()
            
            # Save to Database
            if title and link:
                self.save_job(title, company, link)
                
            yield {
                'title': title,
                'company': company,
                'link': link
            }

    def save_job(self, title, company, url):
        db = SessionLocal()
        try:
            # Avoid duplicates
            existing = db.query(Job).filter_by(job_url=url).first()
            if not existing:
                job = Job(
                    title=title,
                    company=company,
                    job_url=url,
                    scraped_date=datetime.utcnow(),
                    portal="Scrapy-Engine"
                )
                db.add(job)
                db.commit()
        finally:
            db.close()

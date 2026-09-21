from fastapi import FastAPI
from pydantic import BaseModel

from backend.scraper.browser import scrape_website
from backend.analyzer import analyze_website


app = FastAPI(title="DarkShield AI")


class WebsiteRequest(BaseModel):
    url: str


@app.get("/")
def home():
    return {
        "message": "DarkShield AI backend is running"
    }


@app.post("/scan")
def scan_website(request: WebsiteRequest):

    scraped_data = scrape_website(request.url)

    analysis = analyze_website(scraped_data)

    return {
        "website": scraped_data,
        "security_analysis": analysis
    }
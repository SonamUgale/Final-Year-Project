from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.scraper.browser import scrape_website
from backend.analyzer import analyze_website


app = FastAPI(title="DarkShield AI")


# -------------------------------------------------
# CORS
# -------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------
# REQUEST MODEL
# -------------------------------------------------

class WebsiteRequest(BaseModel):
    url: str


# -------------------------------------------------
# HOME
# -------------------------------------------------

@app.get("/")
def home():
    return {
        "message": "DarkShield AI backend is running"
    }


# -------------------------------------------------
# WEBSITE SCAN
# -------------------------------------------------

@app.post("/scan")
def scan_website(request: WebsiteRequest):

    scraped_data = scrape_website(request.url)

    analysis = analyze_website(scraped_data)

    return {
        "website": scraped_data,
        "security_analysis": analysis
    }
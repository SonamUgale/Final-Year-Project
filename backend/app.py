from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.scraper.browser import scrape_website
from backend.analyzer import analyze_website
from backend.ai.llm import get_llm_status
from backend.scan_history import (
    save_scan,
    get_scan_history,
    get_scan_by_id,
    delete_scan,
)
from backend.report_generator import generate_pdf_report


app = FastAPI(title="DarkShield AI")


# -------------------------------------------------
# CORS
# -------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
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
# HOME & HEALTH
# -------------------------------------------------

@app.get("/")
def home():
    ai_ready = False
    try:
        from backend.ai.detector import AIDarkPatternDetector
        ai_ready = AIDarkPatternDetector.get_instance().is_ready()
    except Exception:
        ai_ready = False

    return {
        "message": "DarkShield AI backend is running",
        "ai_engine_ready": ai_ready,
        "llm_status": get_llm_status()
    }


# -------------------------------------------------
# WEBSITE SCAN
# -------------------------------------------------

@app.post("/scan")
def scan_website(request: WebsiteRequest):

    scraped_data = scrape_website(request.url)

    security_analysis = analyze_website(scraped_data)
    dark_pattern_analysis = security_analysis.get("dark_pattern_analysis", {})
    
    ai_analysis = dark_pattern_analysis.get("ai_analysis", {
        "model": "Calibrated Linear SVM + TF-IDF (EC-DarkPattern)",
        "confidence": 0.95,
        "llm_status": get_llm_status()
    })

    scan_result = {
        "website": scraped_data,
        "security_analysis": security_analysis,
        "dark_pattern_analysis": dark_pattern_analysis,
        "ai_analysis": ai_analysis
    }

    # Automatically persist to scan history
    scan_id = save_scan(scan_result)
    scan_result["scan_id"] = scan_id

    return scan_result


# -------------------------------------------------
# SCAN HISTORY ENDPOINTS
# -------------------------------------------------

@app.get("/history")
def get_history(limit: int = 30):
    """Retrieve list of recent scan summaries."""
    return get_scan_history(limit=limit)


@app.get("/history/{scan_id}")
def get_history_detail(scan_id: str):
    """Retrieve full details of a specific past scan."""
    record = get_scan_by_id(scan_id)
    if not record:
        raise HTTPException(status_code=404, detail="Scan record not found")
    return record


@app.delete("/history/{scan_id}")
def delete_history_item(scan_id: str):
    """Delete a past scan by its ID."""
    success = delete_scan(scan_id)
    if not success:
        raise HTTPException(status_code=404, detail="Scan record not found")
    return {"status": "success", "message": f"Scan {scan_id} deleted"}


# -------------------------------------------------
# PDF REPORT ENDPOINTS
# -------------------------------------------------

@app.get("/report/{scan_id}")
def get_pdf_report(scan_id: str):
    """Generate and download a PDF report for an existing scan."""
    record = get_scan_by_id(scan_id)
    if not record:
        raise HTTPException(status_code=404, detail="Scan record not found")

    pdf_buffer = generate_pdf_report(record)
    filename = f"DarkShield_Report_{scan_id}.pdf"

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@app.post("/scan/report")
def scan_and_download_report(request: WebsiteRequest):
    """Scan website and immediately stream back the generated PDF report."""
    scraped_data = scrape_website(request.url)
    security_analysis = analyze_website(scraped_data)
    dark_pattern_analysis = security_analysis.get("dark_pattern_analysis", {})
    ai_analysis = dark_pattern_analysis.get("ai_analysis", {
        "model": "Calibrated Linear SVM + TF-IDF (EC-DarkPattern)",
        "confidence": 0.95,
        "llm_status": get_llm_status()
    })

    scan_result = {
        "website": scraped_data,
        "security_analysis": security_analysis,
        "dark_pattern_analysis": dark_pattern_analysis,
        "ai_analysis": ai_analysis
    }
    scan_id = save_scan(scan_result)
    scan_result["scan_id"] = scan_id

    pdf_buffer = generate_pdf_report(scan_result)
    filename = f"DarkShield_Report_{scan_id}.pdf"

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, Response
from pydantic import BaseModel

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from backend.scraper.browser import scrape_website
from backend.analyzer import analyze_website
from backend.ai.llm import get_llm_status
from backend.ai.vision import get_vision_status
from backend.scan_history import (
    save_scan,
    get_scan_history,
    get_scan_by_id,
    delete_scan,
)
from backend.report_generator import generate_pdf_report
from backend.captured_page import CapturedPage, compare_captures
import threading
import uuid
import base64
import time
from datetime import datetime, timezone
from backend.scraper.crawler import (
    WebsiteCrawler,
    is_ssrf_safe_url,
    normalize_url,
    is_internal_url,
    is_excluded_url,
    extract_internal_links,
    _determine_evidence_type,
    _extract_exact_text,
    _match_selector_and_attrs,
)
from backend.scraper.website_scanner import build_website_scan_summary
from backend.website_history import (
    save_website_scan,
    save_page_snapshot,
    get_website_scan_history,
    get_website_scan_by_id,
    get_website_scan_pages,
    get_page_by_id,
    get_snapshot_path,
    delete_website_scan,
    register_active_crawler,
    get_active_crawler,
    unregister_active_crawler,
    BrowserWebsiteScanSession,
    register_browser_website_session,
    get_browser_website_session,
    unregister_browser_website_session,
)
from backend.website_report_generator import generate_website_pdf_report


app = FastAPI(title="DarkShield AI")


# -------------------------------------------------
# CORS
# -------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_private_network=True,
)


import re
from typing import Optional, List, Dict, Any
from backend.scraper.access_detector import detect_access_block

# -------------------------------------------------
# REQUEST MODELS
# -------------------------------------------------

class WebsiteRequest(BaseModel):
    url: str


class WebsiteScanRequest(BaseModel):
    url: str
    max_pages: Optional[int] = 20
    max_depth: Optional[int] = 2
    concurrency: Optional[int] = 3
    allow_subdomains: Optional[bool] = False
    allow_local: Optional[bool] = False


class BrowserCaptureRequest(BaseModel):
    url: str
    title: Optional[str] = "Captured Webpage"
    html: Optional[str] = ""
    text: Optional[str] = ""
    visible_text: Optional[str] = None
    elements: Optional[List[Dict[str, Any]]] = None
    links: Optional[List[Dict[str, Any]]] = None
    buttons: Optional[List[Dict[str, Any]]] = None
    inputs: Optional[List[Dict[str, Any]]] = None
    dom_elements: Optional[List[Dict[str, Any]]] = None
    cookie_consent: Optional[Dict[str, Any]] = None
    screenshot: Optional[str] = None
    screenshot_b64: Optional[str] = None
    browser_metadata: Optional[Dict[str, Any]] = None


class BrowserWebsiteScanStartRequest(BaseModel):
    url: str
    max_pages: Optional[int] = 20
    max_depth: Optional[int] = 2
    allow_subdomains: Optional[bool] = False
    allow_local: Optional[bool] = True


class BrowserWebsitePageSubmission(BaseModel):
    url: str
    final_url: Optional[str] = None
    title: Optional[str] = "Captured Webpage"
    depth: Optional[int] = 0
    html: Optional[str] = ""
    text: Optional[str] = ""
    visible_text: Optional[str] = None
    elements: Optional[List[Dict[str, Any]]] = None
    screenshot: Optional[str] = None
    browser_metadata: Optional[Dict[str, Any]] = None
    status: Optional[str] = "complete"
    access_blocked: Optional[bool] = False
    block_provider: Optional[str] = None
    discovered_urls: Optional[List[str]] = None


class BrowserWebsiteScanFinishRequest(BaseModel):
    total_discovered: Optional[int] = 0
    scan_status: Optional[str] = "completed"
    limit_reached: Optional[bool] = False


class BrowserWebsiteStageUpdate(BaseModel):
    stage: str
    url: Optional[str] = None
    current_url: Optional[str] = None



def parse_html_to_scraped_data(
    capture_req: Any,
    html: Optional[str] = None,
    title: Optional[str] = None,
    screenshot_b64: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Normalizes user-browser capture payloads into standard scraped_data structure
    expected by the DarkShield analysis pipeline.
    """
    if isinstance(capture_req, str):
        capture_req = BrowserCaptureRequest(
            url=capture_req,
            html=html or "",
            title=title or "Captured Webpage",
            screenshot_b64=screenshot_b64,
        )

    url = capture_req.url
    title = capture_req.title or ""
    html = capture_req.html or ""
    text = capture_req.text or getattr(capture_req, "visible_text", None) or ""
    links = list(capture_req.links or [])
    buttons = list(capture_req.buttons or [])
    inputs = list(capture_req.inputs or [])
    dom_elements = list(capture_req.dom_elements or [])

    # Decompose elements array if provided (e.g. from Chrome Extension)
    raw_elements = getattr(capture_req, "elements", None)
    if raw_elements and isinstance(raw_elements, list):
        for el in raw_elements:
            el_type = str(el.get("element_type", "")).lower()
            tag = str(el.get("tag", "")).lower()
            if el_type == "button" or tag == "button" or el.get("role") == "button":
                if not any(b.get("text") == el.get("text") for b in buttons if b.get("text")):
                    buttons.append(el)
            elif el_type == "link" or tag == "a":
                if not any(l.get("href") == el.get("href") for l in links if l.get("href")):
                    links.append(el)
            elif el_type in ("input", "checkbox", "radio"):
                inputs.append(el)

            dom_elements.append(el)

    # Process screenshot or screenshot_b64
    screenshot_val = (
        getattr(capture_req, "screenshot_b64", None)
        or getattr(capture_req, "screenshot", None)
        or screenshot_b64
    )
    if screenshot_val and isinstance(screenshot_val, str) and screenshot_val.startswith("data:image"):
        parts = screenshot_val.split(",", 1)
        if len(parts) == 2:
            screenshot_val = parts[1]

    # Limit raw HTML string size to 250 KB to eliminate CPU bottlenecks on heavy SPAs
    if html and len(html) > 250000:
        html = html[:250000]

    # If text is not provided, strip scripts and extract text from HTML
    if not text and html:
        clean_h = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", clean_h)
        text = " ".join(text.split())

    # If title not provided, extract <title> from HTML
    if (not title or title == "Captured Webpage") and html:
        t_match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
        if t_match:
            title = t_match.group(1).strip()

    # If links are empty, extract <a> from HTML
    if not links and html:
        for m in re.finditer(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, flags=re.IGNORECASE | re.DOTALL):
            href = m.group(1)
            t = re.sub(r"<[^>]+>", "", m.group(2)).strip()
            if t or href:
                links.append({"text": t[:150], "href": href})
                if len(links) >= 150:
                    break

    # If buttons are empty, extract <button> from HTML
    if not buttons and html:
        for m in re.finditer(r'<button[^>]*>(.*?)</button>', html, flags=re.IGNORECASE | re.DOTALL):
            t = re.sub(r"<[^>]+>", "", m.group(1)).strip()
            if t:
                buttons.append({"text": t[:120]})
                if len(buttons) >= 100:
                    break

    # If inputs are empty, extract <input> placeholders
    if not inputs and html:
        for m in re.finditer(r'<input\s+([^>]+)>', html, flags=re.IGNORECASE):
            attrs = m.group(1)
            p_match = re.search(r'placeholder=["\']([^"\']+)["\']', attrs, flags=re.IGNORECASE)
            t_match = re.search(r'type=["\']([^"\']+)["\']', attrs, flags=re.IGNORECASE)
            n_match = re.search(r'name=["\']([^"\']+)["\']', attrs, flags=re.IGNORECASE)
            inputs.append({
                "type": t_match.group(1) if t_match else "text",
                "name": n_match.group(1) if n_match else None,
                "placeholder": p_match.group(1) if p_match else None
            })
            if len(inputs) >= 60:
                break

    # If dom_elements is empty, extract from headings, paragraphs, and buttons
    if not dom_elements and html:
        for m in re.finditer(r'<h[1-6][^>]*>(.*?)</h[1-6]>', html, flags=re.IGNORECASE | re.DOTALL):
            t = re.sub(r"<[^>]+>", "", m.group(1)).strip()
            if t:
                dom_elements.append({"text": t, "element_type": "heading", "tag": "h"})
        for m in re.finditer(r'<p[^>]*>(.*?)</p>', html, flags=re.IGNORECASE | re.DOTALL):
            t = re.sub(r"<[^>]+>", "", m.group(1)).strip()
            if t:
                dom_elements.append({"text": t, "element_type": "text_block", "tag": "p"})
        for b in buttons:
            if b.get("text"):
                dom_elements.append({"text": b["text"], "element_type": "button", "tag": "button"})

    captured = CapturedPage(
        url=url,
        final_url=url,
        title=title or "Captured Webpage",
        html=html,
        visible_text=text,
        links=links,
        buttons=buttons,
        inputs=inputs,
        forms=[],
        checkboxes=[],
        dom_elements=dom_elements,
        cookie_consent=capture_req.cookie_consent or {},
        headers={},
        screenshot_b64=screenshot_val,
        capture_method="browser_capture",
        capture_status="complete",
        navigation_status="success",
        capture_quality="complete",
        http_status=200,
        access_blocked=False,
        browser_metadata=capture_req.browser_metadata or {},
        scan_duration_seconds=0.5
    )
    return captured.to_dict()


# -------------------------------------------------
# HOME, HEALTH & MODEL METADATA
# -------------------------------------------------

@app.get("/")
def home():
    ai_ready = False
    model_metadata = {}
    try:
        from backend.ai.detector import AIDarkPatternDetector
        detector = AIDarkPatternDetector.get_instance()
        ai_ready = detector.is_ready()
        model_metadata = detector.get_model_metadata()
    except Exception:
        ai_ready = False

    return {
        "message": "DarkShield AI backend is running",
        "ai_engine_ready": ai_ready,
        "llm_status": get_llm_status(),
        "vision_status": get_vision_status(),
        "model_metadata": model_metadata,
        "model_info": model_metadata
    }


@app.get("/model/metadata")
@app.get("/model-info")
def get_model_info():
    """Return verified metadata and evaluation metrics for the active ML model."""
    try:
        from backend.ai.detector import AIDarkPatternDetector
        detector = AIDarkPatternDetector.get_instance()
        return detector.get_model_metadata()
    except Exception as e:
        return {
            "model_name": "Calibrated Linear SVM V2",
            "model_version": "v2",
            "test_accuracy": 0.9689,
            "precision": 0.9672,
            "recall": 0.9710,
            "f1_score": 0.9691,
            "roc_auc": 0.9924,
            "accuracy_display": "96.89%",
            "error": str(e)
        }


import logging

logger = logging.getLogger("darkshield.api")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


# -------------------------------------------------
# WEBSITE SCAN
# -------------------------------------------------

@app.post("/scan")
def scan_website(request: WebsiteRequest):
    logger.info(f"Received scan request for URL: {request.url}")

    # Validate URL structure
    if not request.url or not request.url.strip().startswith(("http://", "https://", "file://")):
        return {
            "status": "invalid_url",
            "scan_status": "failed",
            "navigation_status": "failed",
            "scan_success": False,
            "access_blocked": False,
            "message": "Invalid URL provided. Please provide a valid HTTP or HTTPS URL.",
            "requested_url": request.url,
            "risk_score": None,
            "findings": []
        }

    scraped_data = scrape_website(request.url)

    scan_status = scraped_data.get("scan_status", "complete")
    nav_status = scraped_data.get("navigation_status", "success")
    access_blocked = scraped_data.get("access_blocked", False) or scan_status == "blocked"
    block_provider = scraped_data.get("block_provider")
    http_status = scraped_data.get("http_status", 200)
    warning = scraped_data.get("warning")
    error_type = scraped_data.get("error_type")
    message = scraped_data.get("message")
    duration = scraped_data.get("scan_duration_seconds", 0)

    # 1. Access Blocked Case (HTTP 403, 401, 429, Akamai, Cloudflare, etc.)
    if access_blocked:
        provider = block_provider or "Unknown security/CDN provider"
        msg = f"The website denied automated access ({provider}). Dark-pattern analysis was not performed."
        logger.warning(f"Scan blocked for {request.url} by {provider}")

        security_analysis = analyze_website(scraped_data)
        dark_pattern_analysis = security_analysis.get("dark_pattern_analysis", {})

        scan_result = {
            "status": "blocked",
            "scan_status": "blocked",
            "navigation_status": "blocked",
            "capture_quality": "blocked",
            "capture_method": "automated",
            "scan_mode": "automated",
            "scan_success": False,
            "access_blocked": True,
            "http_status": http_status or 403,
            "block_provider": provider,
            "message": msg,
            "warning": msg,
            "requested_url": request.url,
            "final_url": scraped_data.get("final_url", request.url),
            "scan_duration_seconds": duration,
            "website": scraped_data,
            "security_analysis": security_analysis,
            "dark_pattern_analysis": dark_pattern_analysis,
            "visual_analysis": {
                "available": False,
                "detected": False,
                "visual_risk_score": None,
                "visual_risk_level": "Not Assessed",
                "status": "Blocked"
            },
            "combined_analysis": {
                "combined_risk_score": None,
                "combined_risk_level": "Not Assessed",
                "combined_findings": []
            },
            "ai_analysis": {
                "model": "Calibrated Linear SVM",
                "confidence": 0.0,
                "llm_status": "Skipped (Access Blocked)",
                "vision_status": "Skipped (Access Blocked)"
            },
            "risk_score": None,
            "findings": []
        }
        scan_id = save_scan(scan_result)
        scan_result["scan_id"] = scan_id
        return scan_result

    # 2. Total failure case: Website could not be reached or loaded at all
    if scan_status == "failed":
        if error_type == "navigation_timeout":
            status_label = "timeout"
            clean_msg = "Website did not finish loading within the configured timeout."
        elif error_type in ("dns_failure", "connection_refused", "connection_reset", "connection_closed", "ssl_error", "network_changed"):
            status_label = "network_error"
            clean_msg = message or "Network connection error while connecting to the host."
        else:
            status_label = "scan_error"
            clean_msg = message or "An error occurred while scanning the website."

        logger.warning(f"Scan failed for URL {request.url}: [{error_type}] {clean_msg}")
        scan_result = {
            "status": status_label,
            "scan_status": "failed",
            "navigation_status": nav_status,
            "capture_quality": "partial",
            "capture_method": "automated",
            "scan_mode": "automated",
            "scan_success": False,
            "access_blocked": False,
            "error_type": error_type or "navigation_error",
            "message": clean_msg,
            "requested_url": request.url,
            "final_url": scraped_data.get("final_url", request.url),
            "scan_duration_seconds": duration,
            "website": scraped_data,
            "security_analysis": {
                "security_score": None,
                "risk_level": "Not Assessed",
                "findings": [],
                "total_findings": 0,
                "summary": clean_msg
            },
            "dark_pattern_analysis": {
                "risk_score": None,
                "risk_level": "Not Assessed",
                "risk_breakdown": None,
                "findings": [],
                "total_dark_patterns": 0,
                "summary": clean_msg
            },
            "visual_analysis": {
                "available": False,
                "detected": False,
                "visual_risk_score": None,
                "visual_risk_level": "Not Assessed",
                "visual_confidence": 0.0,
                "total_visual_patterns": 0,
                "patterns": [],
                "analysis_summary": clean_msg,
                "status": "Unavailable"
            },
            "combined_analysis": {
                "combined_risk_score": None,
                "combined_risk_level": "Not Assessed",
                "risk_breakdown": None,
                "combined_findings": [],
                "total_combined_patterns": 0,
                "score_breakdown": [],
                "fusion_summary": clean_msg
            },
            "ai_analysis": {
                "model": "Calibrated Linear SVM",
                "confidence": 0.0,
                "llm_status": "Unavailable",
                "vision_status": "Unavailable"
            },
            "risk_score": None,
            "findings": []
        }
        scan_id = save_scan(scan_result)
        scan_result["scan_id"] = scan_id
        return scan_result

    # 3. Successful scan: DOM content is available and verified accessible
    logger.info(f"Executing security & AI dark pattern analyzers for {request.url} (status: {scan_status})")
    security_analysis = analyze_website(scraped_data)
    dark_pattern_analysis = security_analysis.get("dark_pattern_analysis", {})
    visual_analysis = dark_pattern_analysis.get("visual_analysis", {
        "available": False,
        "status": get_vision_status(),
        "patterns": []
    })
    combined_analysis = dark_pattern_analysis.get("combined_analysis", {})

    ai_analysis = dark_pattern_analysis.get("ai_analysis", {
        "model": "Calibrated Linear SVM + TF-IDF (EC-DarkPattern)",
        "confidence": 0.95,
        "llm_status": get_llm_status(),
        "vision_status": get_vision_status()
    })

    scan_result = {
        "status": "partial" if scan_status == "partial" else "success",
        "scan_status": scan_status,
        "navigation_status": nav_status,
        "capture_quality": scraped_data.get("capture_quality", "complete"),
        "capture_method": "automated",
        "scan_mode": "automated",
        "scan_success": scan_status != "partial",
        "access_blocked": False,
        "warning": warning,
        "requested_url": request.url,
        "final_url": scraped_data.get("final_url", request.url),
        "scan_duration_seconds": duration,
        "website": scraped_data,
        "page_completeness": scraped_data.get("page_completeness", {}),
        "security_analysis": security_analysis,
        "dark_pattern_analysis": dark_pattern_analysis,
        "visual_analysis": visual_analysis,
        "combined_analysis": combined_analysis,
        "ai_analysis": ai_analysis,
        "risk_score": dark_pattern_analysis.get("risk_score"),
        "findings": dark_pattern_analysis.get("findings", [])
    }

    # Automatically persist to scan history
    scan_id = save_scan(scan_result)
    scan_result["scan_id"] = scan_id

    # Store screenshot file on disk and set screenshot_url reference
    raw_b64 = scraped_data.get("screenshot_b64") or scraped_data.get("screenshot")
    if raw_b64 and isinstance(raw_b64, str):
        if "," in raw_b64:
            raw_b64 = raw_b64.split(",", 1)[1]
        try:
            img_bytes = base64.b64decode(raw_b64)
            if img_bytes and len(img_bytes) > 0:
                saved_path = save_page_snapshot(scan_id, "page_1", img_bytes)
                if saved_path:
                    logger.info(f"[DarkShield Scan {scan_id}] Stored viewport snapshot on disk: {saved_path} ({len(img_bytes)} bytes)")
        except Exception as e:
            logger.warning(f"[DarkShield Scan {scan_id}] Failed to persist snapshot file: {e}")

    has_ss = bool(get_snapshot_path(scan_id, "page_1") or raw_b64)
    ss_url = f"/scan/{scan_id}/screenshot" if has_ss else None

    scan_result["has_screenshot"] = has_ss
    scan_result["screenshot_url"] = ss_url
    if "website" in scan_result and isinstance(scan_result["website"], dict):
        scan_result["website"]["has_screenshot"] = has_ss
        scan_result["website"]["screenshot_url"] = ss_url

    return scan_result


# -------------------------------------------------
# BROWSER CAPTURE MODE (Generic Chrome Extension / User-Browser API)
# -------------------------------------------------

@app.post("/scan/capture")
def scan_captured_page(request: BrowserCaptureRequest):
    """
    User-Browser / Chrome Extension Capture Endpoint:
    Accepts HTML/DOM, visible text, interactive elements, and screenshot
    from a legitimate browser session where the user has normal access.
    Feeds into the exact same SVM + rules + Vision AI analysis pipeline.
    """
    logger.info(f"Received browser-capture scan request for URL: {request.url}")

    if not request.url or not request.url.strip().startswith(("http://", "https://", "file://")):
        return {
            "status": "invalid_url",
            "scan_status": "failed",
            "navigation_status": "failed",
            "scan_success": False,
            "access_blocked": False,
            "message": "Invalid URL provided. Please provide a valid HTTP or HTTPS URL.",
            "requested_url": request.url,
            "risk_score": None,
            "findings": []
        }

    scraped_data = parse_html_to_scraped_data(request)

    # Verify captured content is not itself a block or challenge page
    block_info = detect_access_block(
        html=scraped_data.get("html", ""),
        title=scraped_data.get("title", ""),
        text=scraped_data.get("text", ""),
        status_code=200,
        url=request.url
    )
    if block_info["is_blocked"]:
        provider = block_info.get("block_provider") or "Unknown security/CDN provider"
        logger.warning(f"Browser-captured content is a block page: {provider}")
        scraped_data["access_blocked"] = True
        scraped_data["block_provider"] = provider
        scraped_data["scan_status"] = "blocked"
        sec_res = analyze_website(scraped_data)
        dp_res = sec_res.get("dark_pattern_analysis", {})
        return {
            "status": "blocked",
            "scan_mode": "browser_capture",
            "scan_success": False,
            "access_blocked": True,
            "http_status": 403,
            "block_provider": provider,
            "message": f"Captured webpage contains an active {provider} access barrier. Dark-pattern analysis was not performed.",
            "requested_url": request.url,
            "final_url": request.url,
            "security_analysis": sec_res,
            "dark_pattern_analysis": dp_res,
            "risk_score": None,
            "findings": []
        }

    # Run the standard unified DarkShield AI analysis pipeline
    logger.info(f"Analyzing browser-captured webpage for {request.url}")
    security_analysis = analyze_website(scraped_data)
    dark_pattern_analysis = security_analysis.get("dark_pattern_analysis", {})
    visual_analysis = dark_pattern_analysis.get("visual_analysis", {})
    combined_analysis = dark_pattern_analysis.get("combined_analysis", {})
    ai_analysis = dark_pattern_analysis.get("ai_analysis", {})

    is_partial_capture = scraped_data.get("capture_quality") == "partial"
    calculated_score = dark_pattern_analysis.get("risk_score")

    scan_result = {
        "status": "partial" if is_partial_capture else "success",
        "scan_mode": "browser_capture",
        "capture_method": "browser_capture",
        "capture_quality": scraped_data.get("capture_quality", "complete"),
        "scan_status": "partial" if is_partial_capture else "complete",
        "navigation_status": "success",
        "scan_success": not is_partial_capture,
        "access_blocked": False,
        "warning": None,
        "requested_url": request.url,
        "final_url": request.url,
        "scan_duration_seconds": 0.5,
        "website": scraped_data,
        "page_completeness": scraped_data.get("page_completeness", {}),
        "security_analysis": security_analysis,
        "dark_pattern_analysis": dark_pattern_analysis,
        "visual_analysis": visual_analysis,
        "combined_analysis": combined_analysis,
        "ai_analysis": ai_analysis,
        "risk_score": calculated_score,
        "findings": dark_pattern_analysis.get("findings", [])
    }

    scan_id = save_scan(scan_result)
    scan_result["scan_id"] = scan_id

    # Store screenshot file on disk and set screenshot_url reference
    raw_b64 = scraped_data.get("screenshot_b64") or scraped_data.get("screenshot")
    if raw_b64 and isinstance(raw_b64, str):
        if "," in raw_b64:
            raw_b64 = raw_b64.split(",", 1)[1]
        try:
            img_bytes = base64.b64decode(raw_b64)
            if img_bytes and len(img_bytes) > 0:
                saved_path = save_page_snapshot(scan_id, "page_1", img_bytes)
                if saved_path:
                    logger.info(f"[Browser Capture {scan_id}] Stored viewport snapshot on disk: {saved_path} ({len(img_bytes)} bytes)")
        except Exception as e:
            logger.warning(f"[Browser Capture {scan_id}] Failed to persist snapshot file: {e}")

    has_ss = bool(get_snapshot_path(scan_id, "page_1") or raw_b64)
    ss_url = f"/scan/{scan_id}/screenshot" if has_ss else None

    scan_result["has_screenshot"] = has_ss
    scan_result["screenshot_url"] = ss_url
    if "website" in scan_result and isinstance(scan_result["website"], dict):
        scan_result["website"]["has_screenshot"] = has_ss
        scan_result["website"]["screenshot_url"] = ss_url

    return scan_result


# -------------------------------------------------
# DIAGNOSTICS & COMPARISON
# -------------------------------------------------

@app.get("/diagnostics/compare")
def get_capture_comparison(
    url: Optional[str] = None,
    scan_id_auto: Optional[str] = None,
    scan_id_browser: Optional[str] = None
):
    """
    Diagnostic comparison endpoint:
    Compares automated Playwright scan data with user-browser capture data
    for the same URL or scan IDs, reporting metrics disparity and root causes.
    """
    auto_record = None
    browser_record = None

    if scan_id_auto and scan_id_browser:
        auto_record = get_scan_by_id(scan_id_auto)
        browser_record = get_scan_by_id(scan_id_browser)
    elif url:
        all_scans = get_scan_history(limit=50)
        clean_target = url.strip().rstrip("/").lower()
        for s in all_scans:
            sid = s.get("scan_id")
            detail = get_scan_by_id(sid) if sid else None
            if not detail:
                continue
            rec_url = (detail.get("requested_url") or detail.get("final_url") or detail.get("url") or "").strip().rstrip("/").lower()
            if clean_target in rec_url or rec_url in clean_target:
                mode = detail.get("scan_mode") or detail.get("capture_method") or "automated"
                if mode == "browser_capture" and not browser_record:
                    browser_record = detail
                elif mode == "automated" and not auto_record:
                    auto_record = detail

    if not auto_record and not browser_record:
        raise HTTPException(
            status_code=404,
            detail="No matching scan records found for comparison. Please provide a URL scanned in both modes or valid scan IDs."
        )

    auto_data = (auto_record.get("website") if auto_record else {}) or (auto_record or {})
    browser_data = (browser_record.get("website") if browser_record else {}) or (browser_record or {})

    if auto_record:
        auto_data["risk_score"] = auto_record.get("risk_score")
        auto_data["findings"] = auto_record.get("findings")
        auto_data["status"] = auto_record.get("status")
        auto_data["capture_quality"] = auto_record.get("capture_quality", "complete")
        auto_data["capture_method"] = "automated"
    if browser_record:
        browser_data["risk_score"] = browser_record.get("risk_score")
        browser_data["findings"] = browser_record.get("findings")
        browser_data["status"] = browser_record.get("status")
        browser_data["capture_quality"] = browser_record.get("capture_quality", "complete")
        browser_data["capture_method"] = "browser_capture"

    return compare_captures(auto_data, browser_data)


@app.get("/capture/extension-spec")
def get_extension_spec():
    """
    Returns the JSON specification and payload schema for Chrome Extension developers.
    """
    return {
        "endpoint": "POST /scan/capture",
        "format": "application/json",
        "required_fields": ["url"],
        "recommended_fields": ["title", "html", "text", "screenshot_b64"],
        "optional_fields": ["links", "buttons", "inputs", "cookie_consent", "browser_metadata"],
        "extension_architecture": {
            "trigger": "User clicks DarkShield extension icon on active tab",
            "content_script": "Extracts document.title, document.documentElement.outerHTML, document.body.innerText",
            "background_script": "Calls chrome.tabs.captureVisibleTab for JPEG screenshot and POSTs to /scan/capture",
            "response": "Receives full scan result with risk score and findings"
        }
    }


@app.get("/capture/bookmarklet")
def get_capture_bookmarklet():
    """
    Returns a developer utility JavaScript snippet for 1-click browser tab capture.
    """
    code = (
        "javascript:(function(){"
        "const payload={"
        "url:location.href,"
        "title:document.title,"
        "html:document.documentElement.outerHTML,"
        "text:document.body?document.body.innerText:'',"
        "browser_metadata:{userAgent:navigator.userAgent,viewport:{width:window.innerWidth,height:window.innerHeight}}"
        "};"
        "fetch('http://127.0.0.1:8000/scan/capture',{"
        "method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)"
        "}).then(r=>r.json()).then(d=>alert('DarkShield AI Analysis Complete! Risk: '+(d.risk_score??'Blocked')+'/100. Open dashboard to view full report.'))"
        ".catch(e=>alert('DarkShield Capture Failed: '+e));"
        "})();"
    )
    return {"bookmarklet": code, "instructions": "Drag this snippet to your browser bookmarks bar or paste into DevTools console on any protected website."}


# -------------------------------------------------
# SCAN HISTORY ENDPOINTS
# -------------------------------------------------

@app.get("/history/websites")
def get_website_history(limit: int = 30):
    """
    Retrieves recent whole website scans.
    """
    return get_website_scan_history(limit=limit)


@app.delete("/history/website/{scan_id}")
def delete_website_history_item(scan_id: str):
    """
    Deletes a whole website scan by scan_id.
    """
    success = delete_website_scan(scan_id)
    if not success:
        raise HTTPException(status_code=404, detail="Website scan not found")
    return {"status": "success", "message": f"Website scan {scan_id} deleted"}


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
    scan_status = scraped_data.get("scan_status", "complete")
    nav_status = scraped_data.get("navigation_status", "success")
    warning = scraped_data.get("warning")
    error_type = scraped_data.get("error_type")
    message = scraped_data.get("message")
    duration = scraped_data.get("scan_duration_seconds", 0)

    if scan_status == "failed":
        scan_result = {
            "scan_status": "failed",
            "navigation_status": nav_status,
            "error_type": error_type or "navigation_error",
            "message": message or "The website could not be loaded for analysis.",
            "requested_url": request.url,
            "final_url": scraped_data.get("final_url", request.url),
            "scan_duration_seconds": duration,
            "website": scraped_data,
            "security_analysis": {
                "security_score": 0,
                "risk_level": "Unknown",
                "findings": [],
                "total_findings": 0,
                "summary": message or "Scan could not be completed as the host was unreachable."
            },
            "dark_pattern_analysis": {
                "risk_score": 0,
                "risk_level": "None",
                "risk_breakdown": {
                    "severity": 0.0,
                    "confidence": 0.0,
                    "frequency": 0.0,
                    "user_impact": 0.0,
                    "behavioral_evidence": 0.0
                },
                "findings": [],
                "total_dark_patterns": 0,
                "summary": "No page content available for dark pattern detection."
            },
            "visual_analysis": {
                "available": False,
                "detected": False,
                "visual_risk_score": 0,
                "visual_risk_level": "None",
                "visual_confidence": 0.0,
                "total_visual_patterns": 0,
                "patterns": [],
                "analysis_summary": "No visual content available for analysis.",
                "status": get_vision_status()
            },
            "combined_analysis": {
                "combined_risk_score": 0,
                "combined_risk_level": "None",
                "risk_breakdown": {
                    "severity": 0.0,
                    "confidence": 0.0,
                    "frequency": 0.0,
                    "user_impact": 0.0,
                    "behavioral_evidence": 0.0
                },
                "combined_findings": [],
                "total_combined_patterns": 0,
                "score_breakdown": [],
                "fusion_summary": "Scan failed; no multi-modal analysis possible."
            },
            "ai_analysis": {
                "model": "Calibrated Linear SVM + TF-IDF (EC-DarkPattern)",
                "confidence": 0.0,
                "llm_status": get_llm_status(),
                "vision_status": get_vision_status()
            }
        }
    else:
        security_analysis = analyze_website(scraped_data)
        dark_pattern_analysis = security_analysis.get("dark_pattern_analysis", {})
        visual_analysis = dark_pattern_analysis.get("visual_analysis", {
            "available": False,
            "status": get_vision_status(),
            "patterns": []
        })
        combined_analysis = dark_pattern_analysis.get("combined_analysis", {})

        ai_analysis = dark_pattern_analysis.get("ai_analysis", {
            "model": "Calibrated Linear SVM + TF-IDF (EC-DarkPattern)",
            "confidence": 0.95,
            "llm_status": get_llm_status(),
            "vision_status": get_vision_status()
        })

        scan_result = {
            "scan_status": scan_status,
            "navigation_status": nav_status,
            "warning": warning,
            "requested_url": request.url,
            "final_url": scraped_data.get("final_url", request.url),
            "scan_duration_seconds": duration,
            "website": scraped_data,
            "security_analysis": security_analysis,
            "dark_pattern_analysis": dark_pattern_analysis,
            "visual_analysis": visual_analysis,
            "combined_analysis": combined_analysis,
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


# -------------------------------------------------
# WHOLE WEBSITE SCAN ENDPOINTS & BACKGROUND WORKER
# -------------------------------------------------

def _run_website_crawl_job(scan_id: str, crawler: WebsiteCrawler, cfg: Dict[str, Any]):
    """Background worker executing the whole website crawl and persisting the results."""
    import time
    start_time = time.time()
    try:
        pages = crawler.run()
        duration = time.time() - start_time
        summary = build_website_scan_summary(
            base_url=crawler.base_url,
            scan_id=scan_id,
            pages_scanned=pages,
            total_discovered=len(crawler.discovered_urls),
            scan_status="cancelled" if crawler.cancelled else crawler.status,
            duration_seconds=duration,
            limit_reached=getattr(crawler, "limit_reached", False),
            config=cfg,
        )
        save_website_scan(summary, pages)
    except Exception as e:
        logger.error(f"Website crawler background execution error for {scan_id}: {e}", exc_info=True)
        pages = getattr(crawler, "pages_scanned", [])
        duration = time.time() - start_time
        summary = build_website_scan_summary(
            base_url=getattr(crawler, "base_url", ""),
            scan_id=scan_id,
            pages_scanned=pages,
            total_discovered=len(getattr(crawler, "discovered_urls", [])),
            scan_status="failed",
            duration_seconds=duration,
            limit_reached=getattr(crawler, "limit_reached", False),
            config=cfg,
        )
        summary["error"] = str(e)
        save_website_scan(summary, pages)
    finally:
        unregister_active_crawler(scan_id)


@app.post("/scan/website")
def start_website_scan(request: WebsiteScanRequest):
    """
    Initiates an asynchronous multi-page whole website crawl and deceptive design audit.
    """
    raw_url = (request.url or "").strip()
    if not raw_url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=400,
            detail="Invalid URL scheme. Only HTTP and HTTPS URLs are supported."
        )

    # Validate SSRF safety
    is_safe, ssrf_err = is_ssrf_safe_url(raw_url, allow_local=request.allow_local or False)
    if not is_safe:
        raise HTTPException(
            status_code=400,
            detail=f"URL safety check failed: {ssrf_err}"
        )

    # Generate unique scan ID
    now = datetime.now(timezone.utc)
    timestamp_str = now.strftime("%Y%m%d_%H%M%S")
    short_uid = uuid.uuid4().hex[:6]
    scan_id = f"site_scan_{timestamp_str}_{short_uid}"

    max_p = max(1, min(request.max_pages or 100, 150))
    concurrency = max(1, min(request.concurrency or 3, 6))
    max_d = max(0, min(request.max_depth or 2, 5))
    allow_subs = bool(request.allow_subdomains)
    allow_loc = bool(request.allow_local)

    crawler = WebsiteCrawler(
        base_url=raw_url,
        scan_id=scan_id,
        max_pages=max_p,
        max_depth=max_d,
        concurrency=concurrency,
        allow_subdomains=allow_subs,
        allow_local=allow_loc
    )

    register_active_crawler(scan_id, crawler)

    cfg = {
        "max_pages": max_p,
        "max_depth": max_d,
        "concurrency": concurrency,
        "allow_subdomains": allow_subs,
        "allow_local": allow_loc
    }

    thread = threading.Thread(
        target=_run_website_crawl_job,
        args=(scan_id, crawler, cfg),
        daemon=True
    )
    thread.start()

    logger.info(f"Started whole website scan {scan_id} for {raw_url} (max_pages={max_p}, concurrency={concurrency}, max_depth={max_d})")

    return {
        "scan_id": scan_id,
        "status": "crawling",
        "message": "Website crawl started successfully",
        "base_url": crawler.base_url,
        "config": cfg
    }


@app.get("/scan/website/{scan_id}")
def get_website_scan_status(scan_id: str):
    """
    Retrieves the status and summary of a whole website scan.
    Returns live progress if still crawling, or the finalized summary if completed.
    """
    active_crawler = get_active_crawler(scan_id)
    if active_crawler:
        snapshot = active_crawler.get_status_snapshot()
        snapshot["scan_id"] = scan_id
        return snapshot

    browser_session = get_browser_website_session(scan_id)
    if browser_session:
        return browser_session.get_status_snapshot()

    record = get_website_scan_by_id(scan_id)
    if record:
        summary = dict(record.get("summary", {}))
        summary["status"] = summary.get("scan_status", "completed")
        summary["current_stage"] = "Scan completed"
        summary["stage"] = "Scan completed"
        return summary

    raise HTTPException(status_code=404, detail="Website scan not found")


@app.get("/scan/website/{scan_id}/pages")
def get_website_scanned_pages(scan_id: str):
    """
    Returns the array of individual page records for a whole website scan.
    """
    active_crawler = get_active_crawler(scan_id)
    if active_crawler:
        return {
            "scan_id": scan_id,
            "status": active_crawler.status,
            "pages": active_crawler.pages_scanned
        }

    browser_session = get_browser_website_session(scan_id)
    if browser_session:
        return {
            "scan_id": scan_id,
            "status": browser_session.status,
            "pages": browser_session.pages
        }

    pages = get_website_scan_pages(scan_id)
    if pages is not None:
        record = get_website_scan_by_id(scan_id)
        return {
            "scan_id": scan_id,
            "status": record.get("summary", {}).get("scan_status", "completed") if record else "completed",
            "pages": pages
        }

    raise HTTPException(status_code=404, detail="Website scan not found")


@app.get("/scan/website/{scan_id}/pages/{page_id}/screenshot")
def get_website_page_screenshot(scan_id: str, page_id: str):
    """
    Returns the visual snapshot file for a specific page captured during a whole website scan.
    Dynamically identifies MIME type (JPEG, PNG, WebP) and enforces strict path-traversal prevention.
    """
    file_path = get_snapshot_path(scan_id, page_id)
    if not file_path or not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Page snapshot not found")

    ext = os.path.splitext(file_path)[1].lower()
    media_type = "image/jpeg"
    if ext == ".png":
        media_type = "image/png"
    elif ext == ".webp":
        media_type = "image/webp"

    return FileResponse(
        file_path,
        media_type=media_type,
        headers={
            "Cache-Control": "public, max-age=3600",
            "Access-Control-Allow-Origin": "*",
        }
    )


@app.get("/scan/{scan_id}/screenshot")
def get_single_scan_screenshot(scan_id: str):
    """
    Returns the visual snapshot image for a single-page scan result.
    Checks stored disk file first, falling back to base64 decoding and disk caching.
    """
    # 1. Check if snapshot file already exists on disk
    file_path = get_snapshot_path(scan_id, "page_1")
    if file_path and os.path.isfile(file_path):
        ext = os.path.splitext(file_path)[1].lower()
        media_type = "image/png" if ext == ".png" else ("image/webp" if ext == ".webp" else "image/jpeg")
        return FileResponse(
            file_path,
            media_type=media_type,
            headers={
                "Cache-Control": "public, max-age=3600",
                "Access-Control-Allow-Origin": "*",
            }
        )

    # 2. Fallback to reading from scan history record
    scan_data = get_scan_by_id(scan_id)
    if not scan_data:
        raise HTTPException(status_code=404, detail="Scan not found")
    website = scan_data.get("website", {})
    b64_data = website.get("screenshot_b64") or website.get("screenshot")
    if not b64_data:
        raise HTTPException(status_code=404, detail="Screenshot not available for this scan")
    if "," in b64_data:
        b64_data = b64_data.split(",", 1)[1]
    try:
        img_bytes = base64.b64decode(b64_data)
        # Cache to disk for high performance on subsequent requests
        save_page_snapshot(scan_id, "page_1", img_bytes)
    except Exception:
        raise HTTPException(status_code=500, detail="Corrupted screenshot data")

    media_type = "image/jpeg"
    if img_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        media_type = "image/png"
    elif img_bytes.startswith(b"RIFF") and b"WEBP" in img_bytes[:12]:
        media_type = "image/webp"

    return Response(
        content=img_bytes,
        media_type=media_type,
        headers={
            "Cache-Control": "public, max-age=3600",
            "Access-Control-Allow-Origin": "*",
        }
    )


@app.get("/scan/website/{scan_id}/pages/{page_id}")
def get_website_page_detail(scan_id: str, page_id: str):
    """
    Returns the detailed audit record for a single page in a whole website scan.
    """
    active_crawler = get_active_crawler(scan_id)
    if active_crawler:
        for p in active_crawler.pages_scanned:
            if p.get("page_id") == page_id:
                return p

    browser_session = get_browser_website_session(scan_id)
    if browser_session:
        for p in browser_session.pages:
            if p.get("page_id") == page_id:
                return p

    page = get_page_by_id(scan_id, page_id)
    if page:
        return page
    raise HTTPException(status_code=404, detail="Page record not found")


@app.post("/scan/website/{scan_id}/cancel")
def cancel_website_scan(scan_id: str):
    """
    Signals an active website crawler or browser website scan session to cleanly stop early.
    """
    active_crawler = get_active_crawler(scan_id)
    if active_crawler:
        active_crawler.cancel()
        return {
            "scan_id": scan_id,
            "status": "cancelling",
            "message": "Crawler cancellation signaled. Current page will complete before halting."
        }

    browser_session = get_browser_website_session(scan_id)
    if browser_session:
        browser_session.cancel()
        return {
            "scan_id": scan_id,
            "status": "cancelled",
            "message": "Browser website scan cancelled."
        }

    record = get_website_scan_by_id(scan_id)
    if record:
        return {
            "scan_id": scan_id,
            "status": record.get("summary", {}).get("scan_status", "completed"),
            "message": "Website scan already finished."
        }

    raise HTTPException(status_code=404, detail="Website scan not found")


@app.get("/test/timeout")
async def test_timeout_endpoint(delay_sec: float = 8.0):
    """Developer test endpoint that delays response to verify crawler timeout handling."""
    import asyncio
    await asyncio.sleep(delay_sec)
    return {"status": "delayed", "delay_sec": delay_sec}


# -------------------------------------------------
# EXTENSION / USER-BROWSER WHOLE WEBSITE SCAN ENDPOINTS
# -------------------------------------------------

@app.post("/scan/website/browser/start")
def start_browser_website_scan(request: BrowserWebsiteScanStartRequest):
    """
    Initializes a browser-driven whole website scan session for Chrome Extension or user-browser crawling.
    """
    raw_url = (request.url or "").strip()
    if not raw_url.startswith(("http://", "https://", "file://")):
        raise HTTPException(
            status_code=400,
            detail="Invalid URL scheme. Only HTTP, HTTPS, and file URLs are supported."
        )

    # Validate SSRF safety if HTTP/HTTPS
    if raw_url.startswith(("http://", "https://")):
        allow_loc = True if request.allow_local is None else bool(request.allow_local)
        is_safe, ssrf_err = is_ssrf_safe_url(raw_url, allow_local=allow_loc)
        if not is_safe:
            raise HTTPException(
                status_code=400,
                detail=f"URL safety check failed: {ssrf_err}"
            )

    norm_url = normalize_url(raw_url) if raw_url.startswith(("http://", "https://")) else raw_url

    # Generate unique scan ID
    now = datetime.now(timezone.utc)
    timestamp_str = now.strftime("%Y%m%d_%H%M%S")
    short_uid = uuid.uuid4().hex[:6]
    scan_id = f"site_scan_{timestamp_str}_{short_uid}"

    max_p = max(1, min(request.max_pages or 100, 150))
    max_d = max(0, min(request.max_depth or 2, 5))

    cfg = {
        "max_pages": max_p,
        "max_depth": max_d,
        "allow_subdomains": bool(request.allow_subdomains),
        "allow_local": bool(request.allow_local),
        "scan_mode": "browser_capture"
    }

    session = BrowserWebsiteScanSession(
        scan_id=scan_id,
        base_url=norm_url,
        config=cfg
    )
    register_browser_website_session(session)

    logger.info(f"[DarkShield Scan {scan_id}] [Scan started] {norm_url} - max_pages={max_p}, max_depth={max_d}")

    return {
        "scan_id": scan_id,
        "status": "crawling",
        "message": "Browser website scan initialized",
        "base_url": norm_url,
        "config": cfg
    }


@app.post("/scan/website/browser/{scan_id}/stage")
def update_browser_website_stage(scan_id: str, request: BrowserWebsiteStageUpdate):
    """
    Updates the active lifecycle stage and target URL of a running browser website scan.
    """
    session = get_browser_website_session(scan_id)
    if not session:
        return {"status": "not_found", "message": "Session not active"}
    url = request.url or request.current_url
    session.set_stage(request.stage, url)
    return {
        "status": "success",
        "stage": session.current_stage,
        "current_url": session.current_url
    }


@app.post("/scan/website/browser/{scan_id}/page")
def submit_browser_website_page(scan_id: str, request: BrowserWebsitePageSubmission):
    """
    Processes an individual page captured by the user's browser during a website crawl session.
    Runs the exact unified DarkShield AI analysis (SVM V2 + Rules + Risk Scoring).
    Saves snapshot image and enriches findings with selectors, evidence, and reasons.
    """
    session = get_browser_website_session(scan_id)
    if not session:
        existing = get_website_scan_by_id(scan_id)
        if existing:
            raise HTTPException(status_code=400, detail="Website scan is already finalized")
        raise HTTPException(status_code=404, detail="Active browser website scan session not found")

    if session.cancelled:
        return {
            "status": "cancelled",
            "message": "Website scan session has been cancelled."
        }

    t_start = time.time()
    session.current_url = request.url
    session.visited_urls.add(request.url)
    max_pages = session.config.get("max_pages", 100)
    if request.discovered_urls:
        for u in request.discovered_urls:
            if len(session.discovered_urls) >= max_pages:
                break
            session.discovered_urls.add(u)

    session.page_counter += 1
    page_id = f"page_{session.page_counter}"

    logger.info(f"[DarkShield Scan {scan_id}] [Backend analysis requested] {request.url} - Status: {request.status}, Depth: {request.depth}")

    # 1. Handle timed_out status from crawler
    if request.status == "timed_out":
        session.timed_out_count += 1
        page_record = {
            "page_id": page_id,
            "url": request.url,
            "final_url": request.final_url or request.url,
            "title": request.title or "Navigation Timed Out",
            "depth": request.depth or 0,
            "status": "timed_out",
            "capture_quality": "timed_out",
            "capture_method": "browser_capture",
            "access_blocked": False,
            "block_provider": None,
            "risk_score": None,
            "risk_level": "Timed Out",
            "findings_count": 0,
            "findings": [],
            "risk_breakdown": None,
            "security_score": None,
            "scan_duration_seconds": round(time.time() - t_start, 2),
            "discovered_links_count": len(request.discovered_urls or []),
            "has_screenshot": False,
            "screenshot_url": None,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "dom_stats": {"links": 0, "buttons": 0, "inputs": 0, "forms": 0, "checkboxes": 0, "text_chars": 0},
            "text_preview": "",
            "message": "Page navigation or analysis timed out."
        }
    # 2. Handle failed extraction status from crawler
    elif request.status == "failed":
        session.failed_count += 1
        page_record = {
            "page_id": page_id,
            "url": request.url,
            "final_url": request.final_url or request.url,
            "title": request.title or "Extraction Failed",
            "depth": request.depth or 0,
            "status": "failed",
            "capture_quality": "failed",
            "capture_method": "browser_capture",
            "access_blocked": False,
            "block_provider": None,
            "risk_score": None,
            "risk_level": "Failed",
            "findings_count": 0,
            "findings": [],
            "risk_breakdown": None,
            "security_score": None,
            "scan_duration_seconds": round(time.time() - t_start, 2),
            "discovered_links_count": len(request.discovered_urls or []),
            "has_screenshot": False,
            "screenshot_url": None,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "dom_stats": {"links": 0, "buttons": 0, "inputs": 0, "forms": 0, "checkboxes": 0, "text_chars": 0},
            "text_preview": "",
            "message": "Unable to inspect rendered DOM in background session."
        }
    else:
        # 3. Handle block detection
        t_block_start = time.time()
        is_blocked = bool(request.access_blocked)
        block_provider = request.block_provider

        if not is_blocked and request.html:
            block_info = detect_access_block(
                html=request.html,
                title=request.title or "",
                text=request.text or request.visible_text or "",
                status_code=200,
                url=request.url
            )
            if block_info["is_blocked"]:
                is_blocked = True
                block_provider = block_info.get("block_provider") or "Access Barrier"
        t_block = time.time() - t_block_start

        # 4. Save snapshot if screenshot provided
        t_snap_start = time.time()
        has_screenshot = False
        screenshot_url = None
        if request.screenshot and isinstance(request.screenshot, str):
            try:
                b64_data = request.screenshot
                if "," in b64_data:
                    b64_data = b64_data.split(",", 1)[1]
                img_bytes = base64.b64decode(b64_data)
                saved_path = save_page_snapshot(scan_id, page_id, img_bytes)
                if saved_path:
                    has_screenshot = True
                    screenshot_url = f"/scan/website/{scan_id}/pages/{page_id}/screenshot"
            except Exception as e:
                logger.warning(f"Failed to decode/save snapshot for {scan_id}/{page_id}: {e}")
        t_snap = time.time() - t_snap_start

        if is_blocked:
            session.blocked_count += 1
            page_record = {
                "page_id": page_id,
                "url": request.url,
                "final_url": request.final_url or request.url,
                "title": request.title or "Access Blocked",
                "depth": request.depth or 0,
                "status": "blocked",
                "capture_quality": "blocked",
                "capture_method": "browser_capture",
                "access_blocked": True,
                "block_provider": block_provider,
                "risk_score": None,
                "risk_level": "Not Assessed",
                "findings_count": 0,
                "findings": [],
                "risk_breakdown": None,
                "security_score": None,
                "scan_duration_seconds": round(time.time() - t_start, 2),
                "discovered_links_count": len(request.discovered_urls or []),
                "has_screenshot": has_screenshot,
                "screenshot_url": screenshot_url,
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "dom_stats": {
                    "links": 0,
                    "buttons": 0,
                    "inputs": 0,
                    "forms": 0,
                    "checkboxes": 0,
                    "text_chars": len(request.text or request.visible_text or ""),
                },
                "text_preview": (request.text or request.visible_text or "")[:250].strip(),
                "message": f"Scan Incomplete: Access denied by {block_provider or 'WAF / Anti-Bot protection'}."
            }
        else:
            t_parse_start = time.time()
            scraped_data = parse_html_to_scraped_data(
                capture_req=BrowserCaptureRequest(
                    url=request.url,
                    title=request.title or "Captured Webpage",
                    html=request.html or "",
                    text=request.text or "",
                    visible_text=request.visible_text,
                    elements=request.elements or [],
                    screenshot=request.screenshot,
                    browser_metadata=request.browser_metadata or {}
                )
            )
            t_parse = time.time() - t_parse_start

            t_infer_start = time.time()
            analyzed = analyze_website(scraped_data)
            dp_analysis = analyzed.get("dark_pattern_analysis", {})
            risk_score = dp_analysis.get("risk_score")
            risk_level = dp_analysis.get("risk_level", "None")
            raw_findings = dp_analysis.get("findings", [])
            t_infer = time.time() - t_infer_start

            t_enrich_start = time.time()
            candidates = scraped_data.get("dom_elements", [])
            enriched_findings = []
            for f in raw_findings:
                f_copy = dict(f)
                f_copy["page_id"] = page_id
                f_copy["page_url"] = request.url
                f_copy["page_title"] = request.title or "Untitled Webpage"
                f_copy["snapshot_ref"] = screenshot_url
                f_copy["evidence_type"] = _determine_evidence_type(f_copy)
                f_copy["exact_text"] = _extract_exact_text(f_copy)
                sel, attrs = _match_selector_and_attrs(f_copy, candidates)
                f_copy["selector"] = sel
                f_copy["attributes"] = attrs
                if not f_copy.get("reason"):
                    det_m = f_copy.get("detection_method", "Detector")
                    pat_name = f_copy.get("pattern", "Deceptive Pattern")
                    f_copy["reason"] = f_copy.get("description") or f"{det_m} identified '{pat_name}' in page content."
                enriched_findings.append(f_copy)
            t_enrich = time.time() - t_enrich_start

            page_record = {
                "page_id": page_id,
                "url": request.url,
                "final_url": request.final_url or request.url,
                "title": request.title or "Untitled Webpage",
                "depth": request.depth or 0,
                "status": "completed" if (request.status in ("complete", "completed") or not request.status) else request.status,
                "capture_quality": "complete",
                "capture_method": "browser_capture",
                "access_blocked": False,
                "block_provider": None,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "findings_count": len(enriched_findings),
                "findings": enriched_findings,
                "risk_breakdown": dp_analysis.get("risk_breakdown"),
                "security_score": analyzed.get("security_score"),
                "scan_duration_seconds": round(time.time() - t_start, 2),
                "discovered_links_count": len(request.discovered_urls or scraped_data.get("links", [])),
                "has_screenshot": has_screenshot,
                "screenshot_url": screenshot_url,
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "dom_stats": {
                    "links": len(scraped_data.get("links", [])),
                    "buttons": len(scraped_data.get("buttons", [])),
                    "inputs": len(scraped_data.get("inputs", [])),
                    "forms": len(scraped_data.get("forms", [])),
                    "checkboxes": len(scraped_data.get("checkboxes", [])),
                    "text_chars": len(scraped_data.get("text", "")),
                },
                "text_preview": (scraped_data.get("text") or "")[:250].strip()
            }
            if len(enriched_findings) == 0:
                page_record["clean_message"] = "No dark patterns detected on this captured page."

            logger.info(f"[DarkShield Scan {scan_id}] [Risk score calculated] {request.url} - Score: {risk_score}, Level: {risk_level}, Findings: {len(enriched_findings)}")

    session.record_page(page_record)
    session.set_stage(f"Page {len(session.pages)}/{max_pages} processed ({page_record.get('status')})", request.url)
    logger.info(f"[DarkShield Scan {scan_id}] [Result persisted] {request.url} - Total pages saved: {len(session.pages)}")
    logger.info(f"[DarkShield Scan {scan_id}] [Page marked completed] {request.url} - Terminal status: {page_record.get('status')}")

    return {
        "status": "success",
        "page_id": page_id,
        "page_record": page_record,
        "pages_scanned": len(session.pages)
    }


@app.post("/scan/website/browser/{scan_id}/finish")
def finish_browser_website_scan(scan_id: str, request: Optional[BrowserWebsiteScanFinishRequest] = None):
    """
    Finalizes a browser-driven website scan, aggregates website-wide summary,
    and persists records to scan history and index.
    """
    session = get_browser_website_session(scan_id)
    if not session:
        existing = get_website_scan_by_id(scan_id)
        if existing:
            return existing.get("summary", {})
        raise HTTPException(status_code=404, detail="Browser website scan session not found")

    req = request or BrowserWebsiteScanFinishRequest()
    duration = round(time.time() - session.start_time, 2)
    scan_status = req.scan_status or ("cancelled" if session.cancelled else "completed")

    summary = build_website_scan_summary(
        base_url=session.base_url,
        scan_id=scan_id,
        pages_scanned=session.pages,
        total_discovered=min(session.config.get("max_pages", 100), max(len(session.pages), req.total_discovered or len(session.discovered_urls) or len(session.pages))),
        scan_status=scan_status,
        duration_seconds=duration,
        limit_reached=req.limit_reached or session.limit_reached or (len(session.pages) >= session.config.get("max_pages", 100)),
        config=session.config
    )
    summary["scan_mode"] = "browser_capture"

    save_website_scan(summary, session.pages)
    unregister_browser_website_session(scan_id)

    logger.info(f"Finalized browser website scan {scan_id} for {session.base_url}: {len(session.pages)} pages scanned, risk: {summary.get('website_risk_score')}")

    return {
        "scan_id": scan_id,
        "summary": summary,
        "pages_count": len(session.pages)
    }


@app.post("/scan/website/browser/{scan_id}/cancel")
def cancel_browser_website_scan_endpoint(scan_id: str):
    """
    Cancels an active browser website scan session and finalizes whatever pages were scanned.
    """
    session = get_browser_website_session(scan_id)
    if not session:
        record = get_website_scan_by_id(scan_id)
        if record:
            return {
                "scan_id": scan_id,
                "status": record.get("summary", {}).get("scan_status", "completed"),
                "message": "Scan already finished."
            }
        raise HTTPException(status_code=404, detail="Browser website scan session not found")

    session.cancel()
    duration = round(time.time() - session.start_time, 2)
    summary = build_website_scan_summary(
        base_url=session.base_url,
        scan_id=scan_id,
        pages_scanned=session.pages,
        total_discovered=len(session.discovered_urls) or len(session.pages),
        scan_status="cancelled",
        duration_seconds=duration,
        limit_reached=False,
        config=session.config
    )
    summary["scan_mode"] = "browser_capture"
    save_website_scan(summary, session.pages)
    unregister_browser_website_session(scan_id)

    return {
        "scan_id": scan_id,
        "status": "cancelled",
        "summary": summary
    }


@app.get("/report/website/{scan_id}/pdf")
def get_website_pdf_report(scan_id: str):
    """
    Generates and downloads a multi-page PDF report for a whole website scan.
    """
    record = get_website_scan_by_id(scan_id)
    if not record:
        active_crawler = get_active_crawler(scan_id)
        if active_crawler:
            raise HTTPException(
                status_code=400,
                detail="Website scan is currently running. Please wait for completion before downloading PDF report."
            )
        raise HTTPException(status_code=404, detail="Website scan record not found")

    pdf_buffer = generate_website_pdf_report(record)
    filename = f"DarkShield_Website_Report_{scan_id}.pdf"

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@app.get("/test/delay/{seconds}")
def test_delay_endpoint(seconds: int = 5):
    """
    Test endpoint that intentionally delays response to verify timeout handling in crawler.
    """
    time.sleep(seconds)
    return {"status": "delayed", "seconds": seconds}



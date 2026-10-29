"""
DarkShield AI - Whole Website Scan History & Persistence Module
================================================================

Provides persistence and in-memory management for multi-page whole website scans:
- Index summary storage for fast listing of website scans
- Detailed per-scan records with full page audits and findings
- Active crawler registry for real-time progress tracking and cancellation
"""

import os
import json
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
WEBSITE_SCANS_DIR = os.path.join(DATA_DIR, "website_scans")
SNAPSHOTS_DIR = os.path.join(DATA_DIR, "website_snapshots")
INDEX_FILE = os.path.join(DATA_DIR, "website_history_index.json")

# In-memory registry of active crawling jobs: scan_id -> crawler instance or metadata
_ACTIVE_CRAWLERS: Dict[str, Any] = {}
_BROWSER_WEBSITE_SESSIONS: Dict[str, Any] = {}


class BrowserWebsiteScanSession:
    """Tracks state and progress of an extension/browser-driven whole website scan."""

    def __init__(self, scan_id: str, base_url: str, config: Dict[str, Any]):
        import time
        self.scan_id = scan_id
        self.base_url = base_url
        self.config = config
        self.status = "crawling"
        self.start_time = time.time()
        self.current_url = base_url
        self.current_stage = "Scan initialized"
        self.stage = "Scan initialized"
        self.page_counter = 0
        self.pages: List[Dict[str, Any]] = []
        self.discovered_urls: set = {base_url}
        self.visited_urls: set = set()
        self.blocked_count = 0
        self.failed_count = 0
        self.timed_out_count = 0
        self.cancelled = False
        self.limit_reached = False
        self.first_page: Optional[Dict[str, Any]] = None
        self.latest_page: Optional[Dict[str, Any]] = None

    def cancel(self):
        self.cancelled = True
        self.status = "cancelled"
        self.current_stage = "Scan cancelled"
        self.stage = "Scan cancelled"

    def set_stage(self, stage: str, url: Optional[str] = None):
        """Updates the current lifecycle stage and active target URL."""
        self.current_stage = stage
        self.stage = stage
        if url:
            self.current_url = url

    def record_page(self, page_record: Dict[str, Any]):
        """Records a completed page and updates live tracking metadata."""
        self.pages.append(page_record)
        self.latest_page = page_record
        if self.first_page is None:
            self.first_page = page_record

    def get_status_snapshot(self) -> Dict[str, Any]:
        import time
        max_pages = self.config.get("max_pages", 20)
        total_discovered = min(max_pages, max(len(self.pages), len(self.discovered_urls)))
        scanned_count = len(self.pages)
        pct = 0
        if self.status in ("completed", "limit_reached"):
            pct = 100
        elif total_discovered > 0:
            target = min(max_pages, total_discovered)
            pct = min(99, int((scanned_count / max(1, target)) * 100))

        # Live score summaries from first page and current aggregate
        first_page_meta = None
        if self.first_page:
            first_page_meta = {
                "page_id": self.first_page.get("page_id"),
                "url": self.first_page.get("url"),
                "title": self.first_page.get("title"),
                "risk_score": self.first_page.get("risk_score"),
                "risk_level": self.first_page.get("risk_level"),
                "findings_count": self.first_page.get("findings_count", 0),
                "findings": self.first_page.get("findings", [])[:5],
                "access_blocked": bool(self.first_page.get("access_blocked")),
                "status": self.first_page.get("status")
            }

        latest_page_meta = None
        if self.latest_page:
            latest_page_meta = {
                "page_id": self.latest_page.get("page_id"),
                "url": self.latest_page.get("url"),
                "risk_score": self.latest_page.get("risk_score"),
                "risk_level": self.latest_page.get("risk_level"),
                "findings_count": self.latest_page.get("findings_count", 0)
            }

        return {
            "scan_id": self.scan_id,
            "status": self.status,
            "scan_mode": "browser_capture",
            "base_url": self.base_url,
            "current_url": self.current_url,
            "current_stage": self.current_stage,
            "stage": self.stage,
            "pages_discovered": total_discovered,
            "pages_scanned": scanned_count,
            "pages_blocked": self.blocked_count,
            "pages_failed": self.failed_count,
            "pages_timed_out": self.timed_out_count,
            "percent_complete": pct,
            "max_pages": max_pages,
            "max_depth": self.config.get("max_depth", 2),
            "elapsed_seconds": round(time.time() - self.start_time, 1) if self.start_time else 0.0,
            "cancelled": self.cancelled,
            "limit_reached": self.limit_reached,
            "first_page": first_page_meta,
            "latest_page": latest_page_meta
        }


def register_browser_website_session(session: BrowserWebsiteScanSession) -> None:
    """Registers an in-flight browser-driven website scan session."""
    _BROWSER_WEBSITE_SESSIONS[session.scan_id] = session


def get_browser_website_session(scan_id: str) -> Optional[BrowserWebsiteScanSession]:
    """Retrieves an active browser-driven website scan session by scan_id."""
    return _BROWSER_WEBSITE_SESSIONS.get(scan_id)


def unregister_browser_website_session(scan_id: str) -> None:
    """Removes an active browser-driven website scan session once finalized."""
    _BROWSER_WEBSITE_SESSIONS.pop(scan_id, None)



def _ensure_dirs():
    """Ensure persistence directories exist."""
    os.makedirs(WEBSITE_SCANS_DIR, exist_ok=True)
    os.makedirs(SNAPSHOTS_DIR, exist_ok=True)


def register_active_crawler(scan_id: str, crawler: Any) -> None:
    """Registers an in-flight website crawler for progress monitoring and cancellation."""
    _ACTIVE_CRAWLERS[scan_id] = crawler


def get_active_crawler(scan_id: str) -> Optional[Any]:
    """Retrieves an active crawler instance by scan_id."""
    return _ACTIVE_CRAWLERS.get(scan_id)


def unregister_active_crawler(scan_id: str) -> None:
    """Removes an active crawler once finished or terminated."""
    _ACTIVE_CRAWLERS.pop(scan_id, None)


def _load_index() -> List[Dict[str, Any]]:
    """Load the website scan index list from disk."""
    _ensure_dirs()
    if not os.path.exists(INDEX_FILE):
        return []
    try:
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_index(index: List[Dict[str, Any]]) -> None:
    """Save the website scan index list to disk."""
    _ensure_dirs()
    try:
        with open(INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2)
    except Exception as e:
        print(f"[WebsiteHistory] Failed to save index: {e}")


def save_website_scan(scan_summary: Dict[str, Any], pages: List[Dict[str, Any]]) -> str:
    """
    Persists a whole website scan summary and its page records.
    Returns scan_id.
    """
    _ensure_dirs()

    scan_id = scan_summary.get("scan_id")
    now = datetime.now(timezone.utc)
    if not scan_id:
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        short_uid = uuid.uuid4().hex[:6]
        scan_id = f"site_scan_{timestamp_str}_{short_uid}"
        scan_summary["scan_id"] = scan_id

    iso_timestamp = now.isoformat()
    scan_summary["timestamp"] = iso_timestamp

    # Detailed record contains both summary and pages
    record = {
        "scan_id": scan_id,
        "timestamp": iso_timestamp,
        "summary": scan_summary,
        "pages": pages
    }

    # Save detailed scan file
    detailed_filepath = os.path.join(WEBSITE_SCANS_DIR, f"{scan_id}.json")
    try:
        with open(detailed_filepath, "w", encoding="utf-8") as f:
            json.dump(record, f)
    except Exception as e:
        print(f"[WebsiteHistory] Failed to write scan {scan_id}: {e}")

    # Build index summary item
    summary_item = {
        "scan_id": scan_id,
        "timestamp": iso_timestamp,
        "base_url": scan_summary.get("base_url", ""),
        "scan_status": scan_summary.get("scan_status", "completed"),
        "scan_mode": scan_summary.get("scan_mode", "whole_website"),
        "website_risk_score": scan_summary.get("website_risk_score"),
        "website_risk_level": scan_summary.get("website_risk_level", "None"),
        "total_pages_discovered": scan_summary.get("total_pages_discovered", 0),
        "pages_scanned": scan_summary.get("pages_scanned", len(pages)),
        "pages_successful": scan_summary.get("pages_successful", 0),
        "pages_blocked": scan_summary.get("pages_blocked", 0),
        "pages_with_dark_patterns": scan_summary.get("pages_with_dark_patterns", 0),
        "total_unique_findings": scan_summary.get("total_unique_findings", 0),
        "duration_seconds": scan_summary.get("duration_seconds", 0.0)
    }

    # Update index (keep newest first, max 100 entries)
    index = _load_index()
    # Replace existing entry if updating an in-progress scan
    index = [item for item in index if item.get("scan_id") != scan_id]
    index.insert(0, summary_item)
    index = index[:100]
    _save_index(index)

    return scan_id


def get_website_scan_history(limit: int = 30) -> List[Dict[str, Any]]:
    """Retrieve list of whole website scan summaries, ordered newest to oldest."""
    index = _load_index()
    return index[:limit]


def get_website_scan_by_id(scan_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve the full website scan record (summary + pages) by scan_id."""
    _ensure_dirs()
    filepath = os.path.join(WEBSITE_SCANS_DIR, f"{scan_id}.json")
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[WebsiteHistory] Failed to read scan {scan_id}: {e}")
        return None


def get_website_scan_pages(scan_id: str) -> Optional[List[Dict[str, Any]]]:
    """Retrieve only the list of page records for a given website scan_id."""
    record = get_website_scan_by_id(scan_id)
    if record:
        return record.get("pages", [])
    return None


import shutil

def get_snapshot_path(scan_id: str, page_id: str) -> Optional[str]:
    """
    Safely retrieves the absolute path to a page snapshot image,
    enforcing that the target file is strictly within SNAPSHOTS_DIR.
    Checks for .jpg, .jpeg, .png, and .webp extensions and non-empty files.
    """
    if not scan_id or not page_id:
        return None
    target_dir = os.path.join(SNAPSHOTS_DIR, scan_id)
    real_snapshots = os.path.abspath(SNAPSHOTS_DIR)

    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        target_file = os.path.join(target_dir, f"{page_id}{ext}")
        real_target = os.path.abspath(target_file)
        try:
            common = os.path.commonpath([real_target, real_snapshots])
            if common != real_snapshots:
                continue
        except ValueError:
            continue

        if os.path.exists(real_target) and os.path.isfile(real_target) and os.path.getsize(real_target) > 0:
            return real_target
    return None


def save_page_snapshot(scan_id: str, page_id: str, image_bytes: bytes) -> Optional[str]:
    """
    Saves a page screenshot image to the snapshots directory.
    Enforces path traversal safety, detects format (png/jpeg/webp), and returns the absolute path on success.
    """
    if not scan_id or not page_id or not image_bytes or len(image_bytes) == 0:
        return None
    target_dir = os.path.join(SNAPSHOTS_DIR, scan_id)
    
    # Auto-detect image extension from magic bytes
    ext = ".jpg"
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        ext = ".png"
    elif image_bytes.startswith(b"RIFF") and b"WEBP" in image_bytes[:16]:
        ext = ".webp"

    target_file = os.path.join(target_dir, f"{page_id}{ext}")
    real_target = os.path.abspath(target_file)
    real_snapshots = os.path.abspath(SNAPSHOTS_DIR)

    try:
        common = os.path.commonpath([real_target, real_snapshots])
        if common != real_snapshots:
            return None
    except ValueError:
        return None

    try:
        os.makedirs(os.path.dirname(real_target), exist_ok=True)
        with open(real_target, "wb") as f:
            f.write(image_bytes)
        return real_target
    except Exception as e:
        print(f"[WebsiteHistory] Failed to save snapshot for {scan_id}/{page_id}: {e}")
        return None


def get_page_by_id(scan_id: str, page_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single page record by scan_id and page_id."""
    pages = get_website_scan_pages(scan_id)
    if not pages:
        return None
    for p in pages:
        if p.get("page_id") == page_id:
            return p
    return None


def delete_website_scan(scan_id: str) -> bool:
    """Delete a website scan record from disk, index, and remove its snapshots."""
    _ensure_dirs()
    filepath = os.path.join(WEBSITE_SCANS_DIR, f"{scan_id}.json")
    deleted = False
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            deleted = True
        except Exception:
            pass

    # Clean up snapshots directory if it exists
    scan_snapshots_dir = os.path.join(SNAPSHOTS_DIR, scan_id)
    if os.path.exists(scan_snapshots_dir):
        try:
            shutil.rmtree(scan_snapshots_dir, ignore_errors=True)
            deleted = True
        except Exception:
            pass

    index = _load_index()
    new_index = [item for item in index if item.get("scan_id") != scan_id]
    if len(new_index) != len(index):
        _save_index(new_index)
        deleted = True

    return deleted


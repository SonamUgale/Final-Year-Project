"""
DarkShield AI - Scan History & Persistence Module
==================================================

Provides local lightweight JSON persistence for website audits:
- Index summary storage for fast listing
- Detailed per-scan records with full DOM, findings, AI insights, and screenshots
- Querying and retrieval for UI history panel & PDF generation
"""

import os
import json
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
SCANS_DIR = os.path.join(DATA_DIR, "scans")
INDEX_FILE = os.path.join(DATA_DIR, "scan_history_index.json")


def _ensure_dirs():
    """Ensure persistence directories exist."""
    os.makedirs(SCANS_DIR, exist_ok=True)


def _load_index() -> List[Dict[str, Any]]:
    """Load the scan index list from disk."""
    _ensure_dirs()
    if not os.path.exists(INDEX_FILE):
        return []
    try:
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_index(index: List[Dict[str, Any]]) -> None:
    """Save the scan index list to disk."""
    _ensure_dirs()
    try:
        with open(INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2)
    except Exception as e:
        print(f"[ScanHistory] Failed to save index: {e}")


def save_scan(scan_data: Dict[str, Any]) -> str:
    """
    Persist a scan result and update the index.
    Returns the unique scan_id.
    """
    _ensure_dirs()

    # Generate unique scan ID
    now = datetime.now(timezone.utc)
    timestamp_str = now.strftime("%Y%m%d_%H%M%S")
    short_uid = uuid.uuid4().hex[:6]
    scan_id = f"scan_{timestamp_str}_{short_uid}"

    website = scan_data.get("website", {})
    security = scan_data.get("security_analysis", {})
    dark_patterns = scan_data.get("dark_pattern_analysis", {})

    url = website.get("url", "")
    title = website.get("title", "Untitled")
    security_score = security.get("security_score", 100)
    security_risk_level = security.get("risk_level", "Low")
    dark_risk_score = dark_patterns.get("risk_score", 0)
    dark_risk_level = dark_patterns.get("risk_level", "None")
    total_findings = security.get("total_findings", len(security.get("findings", [])))
    total_dark_patterns = dark_patterns.get("total_dark_patterns", len(dark_patterns.get("findings", [])))
    has_screenshot = bool(website.get("screenshot_b64"))

    # Create index summary item
    summary_item = {
        "scan_id": scan_id,
        "timestamp": now.isoformat(),
        "url": url,
        "title": title,
        "security_score": security_score,
        "security_risk_level": security_risk_level,
        "dark_risk_score": dark_risk_score,
        "dark_risk_level": dark_risk_level,
        "total_findings": total_findings,
        "total_dark_patterns": total_dark_patterns,
        "has_screenshot": has_screenshot,
    }

    # Attach scan_id and timestamp to the detailed object
    detailed_record = dict(scan_data)
    detailed_record["scan_id"] = scan_id
    detailed_record["timestamp"] = now.isoformat()

    # Save detailed scan file
    detailed_filepath = os.path.join(SCANS_DIR, f"{scan_id}.json")
    try:
        with open(detailed_filepath, "w", encoding="utf-8") as f:
            json.dump(detailed_record, f)
    except Exception as e:
        print(f"[ScanHistory] Failed to write scan {scan_id}: {e}")

    # Update index (keep newest first, max 100 scans)
    index = _load_index()
    index.insert(0, summary_item)
    index = index[:100]
    _save_index(index)

    return scan_id


def get_scan_history(limit: int = 30) -> List[Dict[str, Any]]:
    """Retrieve list of scan summaries, ordered from newest to oldest."""
    index = _load_index()
    return index[:limit]


def get_scan_by_id(scan_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve the full scan record by scan_id."""
    _ensure_dirs()
    filepath = os.path.join(SCANS_DIR, f"{scan_id}.json")
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ScanHistory] Failed to read scan {scan_id}: {e}")
        return None


def delete_scan(scan_id: str) -> bool:
    """Delete a scan by scan_id from storage and index."""
    _ensure_dirs()
    filepath = os.path.join(SCANS_DIR, f"{scan_id}.json")
    deleted = False
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            deleted = True
        except Exception:
            pass

    index = _load_index()
    new_index = [item for item in index if item.get("scan_id") != scan_id]
    if len(new_index) != len(index):
        _save_index(new_index)
        deleted = True

    return deleted

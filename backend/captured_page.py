"""
DarkShield AI - Common Normalized Page Model & Completeness Engine
===================================================================

Defines:
1. CapturedPage: Standardized internal representation produced by both
   automated Playwright scraping and user-browser capture.
2. evaluate_page_completeness: Objective assessment of DOM structure,
   text volume, and interactive elements to prevent false 'clean' audits
   on incomplete or interstitial pages.
"""

import os
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

# Configurable completeness & scan thresholds
SCAN_TIMEOUT = int(os.getenv("SCAN_TIMEOUT", "30000"))
SCAN_WAIT_AFTER_LOAD = int(os.getenv("SCAN_WAIT_AFTER_LOAD", "2500"))
SCAN_MIN_VISIBLE_TEXT = int(os.getenv("SCAN_MIN_VISIBLE_TEXT", "150"))
SCAN_MIN_DOM_SIZE = int(os.getenv("SCAN_MIN_DOM_SIZE", "1500"))

SUSPICIOUS_TITLES = {
    "",
    "untitled website",
    "untitled",
    "loading...",
    "just a moment...",
    "attention required!",
    "security check",
    "robot check",
    "sorry! something went wrong!",
    "website unavailable"
}


def evaluate_page_completeness(
    url: str,
    title: str,
    html: str,
    text: str,
    links: List[Dict[str, Any]],
    buttons: List[Dict[str, Any]],
    inputs: List[Dict[str, Any]],
    forms: List[Dict[str, Any]],
    http_status: int = 200,
    access_blocked: bool = False,
    block_provider: Optional[str] = None,
    block_reason: Optional[str] = None,
    navigation_status: str = "success",
    capture_method: str = "automated"
) -> Dict[str, Any]:
    """
    Evaluates whether the captured page possesses sufficient rendered content
    for a meaningful deceptive design audit.

    Returns:
        dict: {
            "score": int (0-100),
            "quality": "complete" | "partial" | "blocked",
            "is_complete": bool,
            "is_partial": bool,
            "is_blocked": bool,
            "reasons": List[str],
            "metrics": {
                "text_length": int,
                "html_length": int,
                "links_count": int,
                "buttons_count": int,
                "inputs_count": int,
                "forms_count": int
            }
        }
    """
    clean_text = (text or "").strip()
    clean_html = (html or "").strip()
    clean_title = (title or "").strip()
    lower_title = clean_title.lower()

    text_len = len(clean_text)
    html_len = len(clean_html)
    links_count = len(links or [])
    buttons_count = len(buttons or [])
    inputs_count = len(inputs or [])
    forms_count = len(forms or [])

    metrics = {
        "text_length": text_len,
        "html_length": html_len,
        "links_count": links_count,
        "buttons_count": buttons_count,
        "inputs_count": inputs_count,
        "forms_count": forms_count
    }

    reasons: List[str] = []

    # 1. Blocked Access Case
    if access_blocked or http_status in (401, 403, 429) or (block_provider and block_provider != "None"):
        provider = block_provider or f"HTTP {http_status}"
        reasons.append(f"Automated access was denied or challenged by {provider}.")
        return {
            "score": 0,
            "quality": "blocked",
            "is_complete": False,
            "is_partial": False,
            "is_blocked": True,
            "reasons": reasons,
            "metrics": metrics
        }

    # 2. Check for Incomplete / Suspicious Page Characteristics
    score = 0

    # Title evaluation
    if clean_title and lower_title not in SUSPICIOUS_TITLES:
        score += 15
    else:
        if not clean_title:
            reasons.append("Webpage has no document title.")
        else:
            reasons.append(f"Webpage has placeholder title: '{clean_title}'.")

    # Visible text evaluation
    if text_len >= 1200:
        score += 35
    elif text_len >= 500:
        score += 25
    elif text_len >= SCAN_MIN_VISIBLE_TEXT:
        score += 15
    elif text_len > 0:
        score += 10
    else:
        reasons.append("Webpage has 0 characters of visible text.")

    # HTML structure evaluation
    if html_len >= 10000:
        score += 20
    elif html_len >= SCAN_MIN_DOM_SIZE:
        score += 12
    elif html_len > 0:
        score += 6

    # Interactive elements evaluation
    if links_count >= 10:
        score += 15
    elif links_count > 0:
        score += 8

    if buttons_count >= 3 or inputs_count >= 2 or forms_count >= 1:
        score += 15
    elif buttons_count > 0 or inputs_count > 0:
        score += 8

    # 3. Determine Quality Category
    is_partial = False

    if capture_method == "browser_capture":
        # Browser capture is executed in user's active session
        if text_len == 0 and html_len == 0:
            is_partial = True
            reasons.append("Browser capture payload contained no visible text or HTML.")
        else:
            is_partial = False
            reasons.append("User browser session provided complete rendered DOM.")
            score = max(score, 80)
    else:
        # Automated Playwright crawl quality assessment
        if navigation_status == "timeout":
            is_partial = True
            reasons.append("Navigation timed out before page content could finish loading.")
        elif text_len == 0 and links_count == 0 and buttons_count == 0 and inputs_count == 0:
            is_partial = True
            reasons.append("Page returned completely blank with no visible text or interactive elements.")
        elif lower_title in SUSPICIOUS_TITLES and text_len < 300 and links_count == 0:
            is_partial = True
            reasons.append(f"Webpage has placeholder/interstitial title '{clean_title}' with sparse content.")
        else:
            is_partial = False
            reasons.append("Sufficient DOM structure and visible text retrieved for full audit.")
            score = max(score, 70)

    if is_partial:
        quality = "partial"
        score = min(score, 45)
    else:
        quality = "complete"

    return {
        "score": score,
        "quality": quality,
        "is_complete": quality == "complete",
        "is_partial": quality == "partial",
        "is_blocked": False,
        "reasons": reasons,
        "metrics": metrics
    }


@dataclass
class CapturedPage:
    """
    Standardized Page Representation used by all downstream DarkShield analyzers.
    Normalizes outputs from both Playwright automated scraper and Chrome Extension.
    """
    url: str
    final_url: str = ""
    title: str = ""
    html: str = ""
    visible_text: str = ""
    links: List[Dict[str, Any]] = field(default_factory=list)
    buttons: List[Dict[str, Any]] = field(default_factory=list)
    inputs: List[Dict[str, Any]] = field(default_factory=list)
    forms: List[Dict[str, Any]] = field(default_factory=list)
    checkboxes: List[Dict[str, Any]] = field(default_factory=list)
    dom_elements: List[Dict[str, Any]] = field(default_factory=list)
    cookie_consent: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    screenshot_b64: Optional[str] = None
    capture_method: str = "automated"  # "automated" | "browser_capture"
    capture_status: str = "complete"   # "complete" | "blocked" | "partial" | "timeout" | "failed"
    navigation_status: str = "success" # "success" | "timeout" | "failed" | "blocked"
    capture_quality: str = "complete"  # "complete" | "partial" | "blocked"
    http_status: int = 200
    access_blocked: bool = False
    block_provider: Optional[str] = None
    block_info: Dict[str, Any] = field(default_factory=dict)
    scan_duration_seconds: float = 0.0
    browser_metadata: Dict[str, Any] = field(default_factory=dict)
    page_completeness: Dict[str, Any] = field(default_factory=dict)
    warning: Optional[str] = None
    error_type: Optional[str] = None
    message: Optional[str] = None

    def __post_init__(self):
        if not self.final_url:
            self.final_url = self.url
        if not self.page_completeness:
            self.page_completeness = evaluate_page_completeness(
                url=self.url,
                title=self.title,
                html=self.html,
                text=self.visible_text,
                links=self.links,
                buttons=self.buttons,
                inputs=self.inputs,
                forms=self.forms,
                http_status=self.http_status,
                access_blocked=self.access_blocked,
                block_provider=self.block_provider,
                block_reason=self.block_info.get("reason"),
                navigation_status=self.navigation_status,
                capture_method=self.capture_method
            )
            self.capture_quality = self.page_completeness["quality"]
            if self.page_completeness["is_blocked"]:
                self.access_blocked = True
                self.capture_status = "blocked"
                self.navigation_status = "blocked"
            elif self.page_completeness["is_partial"] and self.capture_status == "complete":
                self.capture_status = "partial"

    @property
    def is_blocked(self) -> bool:
        return self.access_blocked or self.capture_quality == "blocked" or self.capture_status == "blocked"

    @property
    def is_partial(self) -> bool:
        return not self.is_blocked and self.capture_quality == "partial"

    @property
    def is_complete(self) -> bool:
        return not self.is_blocked and self.capture_quality == "complete"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary matching standard scraped_data structure."""
        return {
            "url": self.final_url or self.url,
            "final_url": self.final_url or self.url,
            "requested_url": self.url,
            "title": self.title or ("Access Blocked" if self.is_blocked else ("Incomplete Page" if self.is_partial else "Untitled Website")),
            "html": self.html,
            "text": self.visible_text,
            "visible_text": self.visible_text,
            "links": self.links,
            "buttons": self.buttons,
            "inputs": self.inputs,
            "forms": self.forms,
            "checkboxes": self.checkboxes,
            "dom_elements": self.dom_elements,
            "cookie_consent": self.cookie_consent,
            "headers": self.headers,
            "screenshot_b64": self.screenshot_b64,
            "capture_method": self.capture_method,
            "scan_mode": self.capture_method,
            "capture_status": self.capture_status,
            "status": "blocked" if self.is_blocked else ("partial" if self.is_partial else "complete"),
            "scan_status": self.capture_status if self.capture_status in ("complete", "partial", "blocked", "failed") else ("blocked" if self.is_blocked else ("partial" if self.is_partial else "complete")),
            "navigation_status": self.navigation_status,
            "capture_quality": self.capture_quality,
            "http_status": self.http_status,
            "access_blocked": self.is_blocked,
            "block_provider": self.block_provider,
            "block_info": self.block_info,
            "scan_duration_seconds": self.scan_duration_seconds,
            "browser_metadata": self.browser_metadata,
            "page_completeness": self.page_completeness,
            "warning": self.warning,
            "error_type": self.error_type,
            "message": self.message,
            "scan_success": self.is_complete
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], capture_method: Optional[str] = None) -> "CapturedPage":
        """Instantiate CapturedPage from an existing scraped_data dictionary."""
        method = capture_method or data.get("capture_method") or data.get("scan_mode") or "automated"
        text_val = data.get("visible_text") or data.get("text") or ""

        return cls(
            url=data.get("url") or data.get("requested_url") or "",
            final_url=data.get("final_url") or data.get("url") or "",
            title=data.get("title") or "",
            html=data.get("html") or "",
            visible_text=text_val,
            links=data.get("links") or [],
            buttons=data.get("buttons") or [],
            inputs=data.get("inputs") or [],
            forms=data.get("forms") or [],
            checkboxes=data.get("checkboxes") or [],
            dom_elements=data.get("dom_elements") or [],
            cookie_consent=data.get("cookie_consent") or {},
            headers=data.get("headers") or {},
            screenshot_b64=data.get("screenshot_b64") or data.get("screenshot"),
            capture_method=method,
            capture_status=data.get("capture_status") or data.get("scan_status") or "complete",
            navigation_status=data.get("navigation_status") or "success",
            capture_quality=data.get("capture_quality") or "complete",
            http_status=data.get("http_status", 200),
            access_blocked=data.get("access_blocked", False),
            block_provider=data.get("block_provider"),
            block_info=data.get("block_info") or {},
            scan_duration_seconds=data.get("scan_duration_seconds", 0.0),
            browser_metadata=data.get("browser_metadata") or {},
            page_completeness=data.get("page_completeness") or {},
            warning=data.get("warning"),
            error_type=data.get("error_type"),
            message=data.get("message")
        )


def compare_captures(
    auto_data: Dict[str, Any],
    browser_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Compares automated Playwright scan data with user-browser capture data
    for the same URL, providing diagnostic metrics and explaining any discrepancy.
    """
    url = auto_data.get("url") or browser_data.get("url") or auto_data.get("requested_url") or ""

    auto_text = auto_data.get("visible_text") or auto_data.get("text") or ""
    browser_text = browser_data.get("visible_text") or browser_data.get("text") or ""

    auto_html = auto_data.get("html") or ""
    browser_html = browser_data.get("html") or ""

    auto_blocked = auto_data.get("access_blocked", False) or auto_data.get("status") == "blocked"
    browser_blocked = browser_data.get("access_blocked", False) or browser_data.get("status") == "blocked"

    auto_quality = auto_data.get("capture_quality") or ("blocked" if auto_blocked else "complete")
    browser_quality = browser_data.get("capture_quality") or ("blocked" if browser_blocked else "complete")

    auto_score = auto_data.get("risk_score")
    browser_score = browser_data.get("risk_score")

    auto_findings = auto_data.get("findings") or auto_data.get("dark_pattern_analysis", {}).get("findings") or []
    browser_findings = browser_data.get("findings") or browser_data.get("dark_pattern_analysis", {}).get("findings") or []

    auto_patterns = len(auto_findings)
    browser_patterns = len(browser_findings)

    auto_links = len(auto_data.get("links") or [])
    browser_links = len(browser_data.get("links") or [])

    auto_buttons = len(auto_data.get("buttons") or [])
    browser_buttons = len(browser_data.get("buttons") or [])

    auto_inputs = len(auto_data.get("inputs") or [])
    browser_inputs = len(browser_data.get("inputs") or [])

    comparison = {
        "url": url,
        "automated": {
            "method": "automated",
            "status": auto_data.get("status") or auto_data.get("scan_status"),
            "quality": auto_quality,
            "access_blocked": auto_blocked,
            "block_provider": auto_data.get("block_provider"),
            "html_length": len(auto_html),
            "text_length": len(auto_text),
            "links_count": auto_links,
            "buttons_count": auto_buttons,
            "inputs_count": auto_inputs,
            "has_screenshot": bool(auto_data.get("screenshot_b64")),
            "risk_score": auto_score,
            "detected_patterns": auto_patterns
        },
        "browser_capture": {
            "method": "browser_capture",
            "status": browser_data.get("status") or browser_data.get("scan_status"),
            "quality": browser_quality,
            "access_blocked": browser_blocked,
            "block_provider": browser_data.get("block_provider"),
            "html_length": len(browser_html),
            "text_length": len(browser_text),
            "links_count": browser_links,
            "buttons_count": browser_buttons,
            "inputs_count": browser_inputs,
            "has_screenshot": bool(browser_data.get("screenshot_b64")),
            "risk_score": browser_score,
            "detected_patterns": browser_patterns
        },
        "differences": {
            "html_diff_bytes": len(browser_html) - len(auto_html),
            "text_diff_chars": len(browser_text) - len(auto_text),
            "links_diff": browser_links - auto_links,
            "buttons_diff": browser_buttons - auto_buttons,
            "inputs_diff": browser_inputs - auto_inputs,
            "score_diff": (browser_score - auto_score) if (browser_score is not None and auto_score is not None) else None
        }
    }

    if auto_blocked and not browser_blocked:
        provider = auto_data.get("block_provider") or "Anti-bot / WAF protection"
        conclusion = (
            f"Discrepancy Explained: Automated Playwright scan was blocked by {provider}. "
            f"The server returned an access challenge/interstitial page without rendering the actual web application. "
            f"In contrast, Browser Capture extracted the fully rendered DOM from the user's normal browser session "
            f"({len(browser_text)} chars of text, {browser_buttons} buttons), "
            f"enabling DarkShield to audit deceptive design and calculate a verified Risk Score ({browser_score}/100)."
        )
    elif auto_quality == "partial" and browser_quality == "complete":
        conclusion = (
            f"Discrepancy Explained: Automated scan captured incomplete DOM content ({len(auto_text)} text chars). "
            f"DarkShield safely withheld risk scoring (status: PARTIAL) to avoid a misleading 'clean' score. "
            f"Browser Capture provided the full rendered DOM ({len(browser_text)} text chars), producing a verified audit."
        )
    elif auto_score == browser_score:
        conclusion = "Both automated scan and browser capture received equivalent content and produced matching risk assessments."
    else:
        conclusion = (
            f"Content disparity: Browser capture received {len(browser_text)} chars vs {len(auto_text)} chars in automated scan. "
            f"Risk score in browser capture is {browser_score} vs {auto_score} in automated scan."
        )

    comparison["conclusion"] = conclusion
    return comparison


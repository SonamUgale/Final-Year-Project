from urllib.parse import urlparse
from typing import Dict, Any, Union

from backend.detectors.dark_patterns import detect_dark_patterns
from backend.captured_page import CapturedPage


def analyze_page(captured_page: Union[CapturedPage, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Unified Downstream Analysis Pipeline for both Automated Scan and Browser Capture.
    Guarantees that both modes pass through identical preprocessing, SVM V2,
    rule detection, evidence validation, and 5-factor risk scoring.
    """
    if not isinstance(captured_page, CapturedPage):
        if isinstance(captured_page, dict):
            page_obj = CapturedPage.from_dict(captured_page)
        else:
            page_obj = CapturedPage(url=str(captured_page))
    else:
        page_obj = captured_page

    scraped_data = page_obj.to_dict()

    # 1. Guard against blocked pages: Never analyze access denied / challenge pages
    if page_obj.is_blocked:
        provider = page_obj.block_provider or "Unknown security/CDN provider"
        http_status = page_obj.http_status or 403
        msg = f"The website denied automated access ({provider}). Dark-pattern analysis was not performed."
        print(f"[Scanner] Dark-pattern analysis skipped (access blocked: provider={provider})")

        return {
            "status": "blocked",
            "capture_quality": "blocked",
            "capture_method": page_obj.capture_method,
            "scan_mode": page_obj.capture_method,
            "scan_success": False,
            "access_blocked": True,
            "http_status": http_status,
            "block_provider": provider,
            "message": msg,
            "warning": msg,
            "risk_level": "Not Assessed",
            "security_score": None,
            "risk_score": None,
            "total_patterns": 0,
            "total_findings": 0,
            "findings": [],
            "page_completeness": page_obj.page_completeness,
            "dark_pattern_analysis": {
                "status": "blocked",
                "capture_quality": "blocked",
                "scan_success": False,
                "access_blocked": True,
                "http_status": http_status,
                "block_provider": provider,
                "message": msg,
                "findings": [],
                "risk_score": None,
                "risk_level": "Not Assessed",
                "risk_breakdown": None,
                "summary": msg,
                "total_dark_patterns": 0
            }
        }

    # 2. Guard against incomplete / partial pages: Never assign false 'clean' score (0/100)
    if page_obj.is_partial:
        reasons_list = page_obj.page_completeness.get("reasons", ["Incomplete page content retrieved"])
        msg = (
            "Automated scan captured incomplete page content. "
            "Risk scoring was withheld to avoid a false clean result. Try Browser Capture."
        )
        print(f"[Scanner] Dark-pattern analysis withheld (partial capture: {'; '.join(reasons_list)})")

    findings = []
    score = 100

    url = scraped_data.get("url", "")
    links = scraped_data.get("links", [])
    inputs = scraped_data.get("inputs", [])
    buttons = scraped_data.get("buttons", [])
    headers = scraped_data.get("headers", {})

    parsed_url = urlparse(url)

    # Run complete dark pattern detector pipeline if complete, else withhold
    if page_obj.is_partial:
        dark_pattern_analysis = {
            "status": "partial",
            "capture_quality": "partial",
            "scan_success": False,
            "access_blocked": False,
            "http_status": page_obj.http_status or 200,
            "block_provider": None,
            "message": msg,
            "findings": [],
            "risk_score": None,
            "risk_level": "Not Assessed (Incomplete Capture)",
            "risk_breakdown": None,
            "summary": msg,
            "total_dark_patterns": 0
        }
    else:
        print("[Scanner] Running SVM")
        print("[Scanner] Running rules")
        print("[Scanner] Running Vision AI")
        print("[Scanner] Calculating risk score")
        dark_pattern_analysis = detect_dark_patterns(scraped_data)

    # Convert header names to lowercase
    headers = {
        key.lower(): value
        for key, value in headers.items()
    }

    # -------------------------------------------------
    # 1. HTTPS CHECK
    # -------------------------------------------------

    if parsed_url.scheme != "https":

        findings.append({
            "issue": "Website is not using HTTPS",
            "severity": "High",
            "description": "The website is using HTTP instead of HTTPS."
        })

        score -= 30

    # -------------------------------------------------
    # 2. PASSWORD INPUT CHECK
    # -------------------------------------------------

    password_fields = []

    for field in inputs:

        if field.get("type") == "password":
            password_fields.append(field)

    if password_fields and parsed_url.scheme != "https":

        findings.append({
            "issue": "Password field detected on non-HTTPS website",
            "severity": "Critical",
            "description": (
                "A password input is present while the website "
                "is not using HTTPS."
            )
        })

        score -= 40

    # -------------------------------------------------
    # 3. CONTENT SECURITY POLICY
    # -------------------------------------------------

    if "content-security-policy" not in headers:

        findings.append({
            "issue": "Missing Content-Security-Policy header",
            "severity": "Medium",
            "description": (
                "The website does not define a "
                "Content-Security-Policy header."
            )
        })

        score -= 10

    # -------------------------------------------------
    # 4. X-FRAME-OPTIONS
    # -------------------------------------------------

    if "x-frame-options" not in headers:

        findings.append({
            "issue": "Missing X-Frame-Options header",
            "severity": "Medium",
            "description": (
                "The website does not define X-Frame-Options "
                "protection against clickjacking."
            )
        })

        score -= 10

    # -------------------------------------------------
    # 5. X-CONTENT-TYPE-OPTIONS
    # -------------------------------------------------

    if "x-content-type-options" not in headers:

        findings.append({
            "issue": "Missing X-Content-Type-Options header",
            "severity": "Low",
            "description": (
                "The website does not define X-Content-Type-Options "
                "to help prevent MIME-type sniffing."
            )
        })

        score -= 5

    # -------------------------------------------------
    # 6. STRICT-TRANSPORT-SECURITY
    # -------------------------------------------------

    if parsed_url.scheme == "https":

        if "strict-transport-security" not in headers:

            findings.append({
                "issue": "Missing Strict-Transport-Security header",
                "severity": "Medium",
                "description": (
                    "The HTTPS website does not define "
                    "HSTS protection."
                )
            })

            score -= 10

    # -------------------------------------------------
    # 7. EXTERNAL LINK CHECK
    # -------------------------------------------------

    external_links = []

    for link in links:

        href = link.get("href")

        if not href:
            continue

        if href.startswith("http://") or href.startswith("https://"):

            link_domain = urlparse(href).netloc

            if link_domain and link_domain != parsed_url.netloc:

                external_links.append(href)

    if external_links:

        findings.append({
            "issue": "External links detected",
            "severity": "Info",
            "description": (
                f"The website contains {len(external_links)} "
                "links pointing to external domains."
            )
        })

    # -------------------------------------------------
    # 8. SUSPICIOUS LINK CHECK
    # -------------------------------------------------

    suspicious_links = []

    for link in links:

        href = link.get("href")

        if not href:
            continue

        href_lower = href.lower()

        if (
            href_lower.startswith("javascript:")
            or href_lower.startswith("data:")
        ):

            suspicious_links.append(href)

    if suspicious_links:

        findings.append({
            "issue": "Suspicious links detected",
            "severity": "Medium",
            "description": (
                f"The website contains {len(suspicious_links)} "
                "potentially suspicious links."
            )
        })

        score -= 15

    # -------------------------------------------------
    # 9. INPUT FIELD CHECK
    # -------------------------------------------------

    if inputs:

        findings.append({
            "issue": "User input fields detected",
            "severity": "Info",
            "description": (
                f"The website contains {len(inputs)} input field(s)."
            )
        })

    # -------------------------------------------------
    # 10. BUTTON CHECK
    # -------------------------------------------------

    if buttons:

        findings.append({
            "issue": "Interactive buttons detected",
            "severity": "Info",
            "description": (
                f"The website contains {len(buttons)} button(s)."
            )
        })

    # -------------------------------------------------
    # FINAL SCORE
    # -------------------------------------------------

    score = max(0, score)

    if score >= 80:

        risk_level = "Low"

    elif score >= 50:

        risk_level = "Medium"

    else:

        risk_level = "High"

    # Critical issue always means High risk
    for finding in findings:

        if finding["severity"] == "Critical":

            risk_level = "High"
            break

    # -------------------------------------------------
    # RETURN SECURITY & DARK PATTERN REPORT
    # -------------------------------------------------

    return {
        "status": "partial" if page_obj.is_partial else "complete",
        "capture_quality": page_obj.capture_quality,
        "capture_method": page_obj.capture_method,
        "scan_mode": page_obj.capture_method,
        "scan_success": not page_obj.is_partial,
        "access_blocked": False,
        "risk_level": risk_level,
        "security_score": score,
        "risk_score": dark_pattern_analysis.get("risk_score"),
        "total_findings": len(findings),
        "findings": findings,
        "page_completeness": page_obj.page_completeness,
        "dark_pattern_analysis": dark_pattern_analysis
    }


def analyze_website(scraped_data: Any) -> Dict[str, Any]:
    """Compatibility wrapper redirecting to the unified analyze_page pipeline."""
    return analyze_page(scraped_data)
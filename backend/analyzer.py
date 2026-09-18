from urllib.parse import urlparse


def analyze_website(scraped_data):

    findings = []
    score = 100

    url = scraped_data["url"]
    links = scraped_data.get("links", [])
    inputs = scraped_data.get("inputs", [])
    buttons = scraped_data.get("buttons", [])
    headers = scraped_data.get("headers", {})

    parsed_url = urlparse(url)

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
            "description": "A password input is present while the website is not using HTTPS."
        })

        score -= 40

    # -------------------------------------------------
    # 3. CONTENT SECURITY POLICY
    # -------------------------------------------------

    if "content-security-policy" not in headers:

        findings.append({
            "issue": "Missing Content-Security-Policy header",
            "severity": "Medium",
            "description": "The website does not define a Content-Security-Policy header."
        })

        score -= 10

    # -------------------------------------------------
    # 4. X-FRAME-OPTIONS
    # -------------------------------------------------

    if "x-frame-options" not in headers:

        findings.append({
            "issue": "Missing X-Frame-Options header",
            "severity": "Medium",
            "description": "The website does not define X-Frame-Options protection against clickjacking."
        })

        score -= 10

    # -------------------------------------------------
    # 5. X-CONTENT-TYPE-OPTIONS
    # -------------------------------------------------

    if "x-content-type-options" not in headers:

        findings.append({
            "issue": "Missing X-Content-Type-Options header",
            "severity": "Low",
            "description": "The website does not define X-Content-Type-Options to help prevent MIME-type sniffing."
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
                "description": "The HTTPS website does not define HSTS protection."
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
            "description": f"The website contains {len(external_links)} links pointing to external domains."
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
            "description": f"The website contains {len(suspicious_links)} potentially suspicious links."
        })

        score -= 15

    # -------------------------------------------------
    # 9. INPUT FIELD CHECK
    # -------------------------------------------------

    if inputs:

        findings.append({
            "issue": "User input fields detected",
            "severity": "Info",
            "description": f"The website contains {len(inputs)} input field(s)."
        })

    # -------------------------------------------------
    # 10. BUTTON CHECK
    # -------------------------------------------------

    if buttons:

        findings.append({
            "issue": "Interactive buttons detected",
            "severity": "Info",
            "description": f"The website contains {len(buttons)} button(s)."
        })

    # -------------------------------------------------
    # FINAL SCORE
    # -------------------------------------------------

    score = max(0, score)

    # Determine risk level
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
    # RETURN SECURITY REPORT
    # -------------------------------------------------

    return {
        "risk_level": risk_level,
        "security_score": score,
        "total_findings": len(findings),
        "findings": findings
    }
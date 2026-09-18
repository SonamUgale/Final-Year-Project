import re


def detect_dark_patterns(scraped_data):

    findings = []

    text = scraped_data.get("text", "")
    links = scraped_data.get("links", [])
    buttons = scraped_data.get("buttons", [])
    inputs = scraped_data.get("inputs", [])

    # Convert page text to lowercase
    page_text = text.lower()

    # -------------------------------------------------
    # 1. URGENCY / SCARCITY
    # -------------------------------------------------

    urgency_patterns = [
        r"limited time",
        r"only \d+ left",
        r"\d+ left",
        r"hurry",
        r"act now",
        r"last chance",
        r"offer expires",
        r"ends today",
        r"ending soon",
        r"limited offer"
    ]

    urgency_matches = []

    for pattern in urgency_patterns:

        matches = re.findall(pattern, page_text)

        urgency_matches.extend(matches)

    if urgency_matches:

        findings.append({
            "pattern": "Urgency or Scarcity",
            "severity": "Medium",
            "description": (
                "The website contains language that may create "
                "a sense of urgency or scarcity."
            ),
            "evidence": list(set(urgency_matches))
        })

    # -------------------------------------------------
    # 2. CONFIRMSHAMING
    # -------------------------------------------------

    confirmshaming_patterns = [
        r"no thanks",
        r"no,? i don't want",
        r"i don't want",
        r"i prefer",
        r"skip.*saving",
        r"continue without"
    ]

    confirmshaming_matches = []

    for pattern in confirmshaming_patterns:

        matches = re.findall(pattern, page_text)

        confirmshaming_matches.extend(matches)

    if confirmshaming_matches:

        findings.append({
            "pattern": "Confirmshaming",
            "severity": "Medium",
            "description": (
                "The website may use language that makes "
                "declining an offer appear undesirable."
            ),
            "evidence": list(set(confirmshaming_matches))
        })

    # -------------------------------------------------
    # 3. AGGRESSIVE CALL TO ACTION
    # -------------------------------------------------

    cta_keywords = [
        "buy now",
        "subscribe now",
        "sign up now",
        "get started now",
        "claim now",
        "order now",
        "download now"
    ]

    cta_matches = []

    for button in buttons:

        button_text = button.get("text", "").lower().strip()

        for keyword in cta_keywords:

            if keyword in button_text:
                cta_matches.append(button_text)

    if cta_matches:

        findings.append({
            "pattern": "Aggressive Call To Action",
            "severity": "Low",
            "description": (
                "The website contains strong call-to-action "
                "messages encouraging immediate action."
            ),
            "evidence": list(set(cta_matches))
        })

    # -------------------------------------------------
    # 4. FORCED REGISTRATION
    # -------------------------------------------------

    account_keywords = [
        "create account",
        "sign up",
        "register",
        "log in",
        "login"
    ]

    account_related = []

    for button in buttons:

        button_text = button.get("text", "").lower().strip()

        for keyword in account_keywords:

            if keyword in button_text:
                account_related.append(button_text)

    if account_related and inputs:

        findings.append({
            "pattern": "Potential Forced Registration",
            "severity": "Medium",
            "description": (
                "The page contains account-related actions "
                "along with input fields."
            ),
            "evidence": list(set(account_related))
        })

    # -------------------------------------------------
    # 5. EXCESSIVE EXTERNAL LINKS
    # -------------------------------------------------

    external_links = []

    for link in links:

        href = link.get("href")

        if href and (
            href.startswith("http://")
            or href.startswith("https://")
        ):

            external_links.append(href)

    if len(external_links) > 10:

        findings.append({
            "pattern": "Large Number of External Links",
            "severity": "Low",
            "description": (
                f"The website contains {len(external_links)} "
                "external links."
            ),
            "evidence": external_links[:10]
        })

    # -------------------------------------------------
    # FINAL RESULT
    # -------------------------------------------------

    return {
        "total_dark_patterns": len(findings),
        "findings": findings
    }
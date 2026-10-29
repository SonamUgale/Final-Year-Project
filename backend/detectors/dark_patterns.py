"""
DarkShield AI - Hybrid Dark Pattern Detection Engine
=====================================================

Combines:
1. Supervised Machine Learning (Calibrated Linear SVM + Multiclass Classifier)
2. Rule-Based Supporting Signals (Regex & Structural DOM Checks)
3. DOM Context & Element Metadata (Tag, Element Type, Surrounding Context)
4. Explainable Dark Pattern Risk Scoring (0-100)
5. LLM Contextual Interpretation (Explanations, Impact, Recommendations)

Decision Fusion Logic:
- If both ML model and Rule detector flag a related pattern:
    -> detection_method = 'Hybrid (Rules + AI)'
    -> Evidence snippets fused and deduplicated
    -> Confidence reflects multi-signal reinforcement: min(0.999, max(c_ml, c_rule) + 0.05)
- If flagged only by ML (e.g. Social Proof, subtle Scarcity, Sneaking):
    -> detection_method = 'AI Model'
    -> Confidence = calibrated ML probability
- If flagged only by Rules (e.g. excessive external link counts, forced registration form):
    -> detection_method = 'Rule-Based'
    -> Confidence = heuristic baseline (0.70 - 0.75)
"""

import re
from urllib.parse import urlparse
from typing import Dict, Any, List

from backend.detectors.scoring import calculate_dark_pattern_risk, calculate_multimodal_risk
from backend.ai.llm import enrich_findings_with_llm, get_llm_status
from backend.ai.vision import analyze_screenshot, get_vision_status

# Try importing AI detector gracefully
try:
    from backend.ai.detector import AIDarkPatternDetector
    ai_detector = AIDarkPatternDetector.get_instance()
except Exception as e:
    ai_detector = None
    print(f"[DarkPatterns] AI detector unavailable: {e}")


def detect_dark_patterns_rule_based(scraped_data: Dict[str, Any]) -> Dict[str, Any]:
    """Original rule-based dark pattern detection logic."""
    findings = []

    text = scraped_data.get("text", "")
    links = scraped_data.get("links", [])
    buttons = scraped_data.get("buttons", [])
    inputs = scraped_data.get("inputs", [])

    page_text = text.lower()

    # 1. URGENCY / SCARCITY
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
            "detection_method": "Rule-Based",
            "confidence": 0.85,
            "element_type": "text_block",
            "description": "The website contains language that may create a sense of urgency or scarcity.",
            "evidence": list(set(urgency_matches)),
            "rule_signals": ["urgency_scarcity_regex"]
        })

    # 2. CONFIRMSHAMING
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
            "detection_method": "Rule-Based",
            "confidence": 0.85,
            "element_type": "text_block",
            "description": "The website may use language that makes declining an offer appear undesirable.",
            "evidence": list(set(confirmshaming_matches)),
            "rule_signals": ["confirmshaming_regex"]
        })

    # 3. AGGRESSIVE CALL TO ACTION
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
            "detection_method": "Rule-Based",
            "confidence": 0.80,
            "element_type": "button",
            "description": "The website contains strong call-to-action messages encouraging immediate action.",
            "evidence": list(set(cta_matches)),
            "rule_signals": ["cta_button_keywords"]
        })

    # 4. FORCED REGISTRATION
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
            "detection_method": "Rule-Based",
            "confidence": 0.75,
            "element_type": "form_input",
            "description": "The page contains account-related actions along with input fields.",
            "evidence": list(set(account_related)),
            "rule_signals": ["account_button_with_inputs"]
        })

    # 5. EXCESSIVE EXTERNAL / REDIRECT LINKS
    target_url = scraped_data.get("url", "")
    target_domain = ""
    if target_url:
        try:
            target_domain = urlparse(target_url).netloc.lower().split(":")[0]
            if target_domain.startswith("www."):
                target_domain = target_domain[4:]
        except Exception:
            target_domain = ""

    external_links = []
    for link in links:
        href = link.get("href")
        if href and (href.startswith("http://") or href.startswith("https://")):
            try:
                link_domain = urlparse(href).netloc.lower().split(":")[0]
                if link_domain.startswith("www."):
                    link_domain = link_domain[4:]
                # Link is genuinely external if domain differs and is not an internal subdomain
                if target_domain and link_domain and not (link_domain == target_domain or link_domain.endswith("." + target_domain)):
                    external_links.append(href)
            except Exception:
                pass

    # Flag only if there is an overwhelmingly abnormal ratio of third-party outbound links (>40 links and >50% of total)
    total_links_count = len(links)
    if len(external_links) >= 40 and total_links_count > 0 and (len(external_links) / total_links_count) > 0.50:
        findings.append({
            "pattern": "Large Number of External Links",
            "severity": "Low",
            "detection_method": "Rule-Based",
            "confidence": 0.70,
            "element_type": "link",
            "description": f"The website contains an unusually high ratio of third-party external links ({len(external_links)} links).",
            "evidence": external_links[:10],
            "rule_signals": ["high_external_link_count"]
        })

    # 6. COOKIE CONSENT & PRIVACY DARK PATTERNS
    cookie_data = scraped_data.get("cookie_consent", {})
    if cookie_data.get("banner_detected"):
        accept_btn = cookie_data.get("accept_button")
        reject_btn = cookie_data.get("reject_button")
        manage_btn = cookie_data.get("manage_button")
        preselected = cookie_data.get("preselected_checkboxes", [])
        banner_text = cookie_data.get("banner_text", "")

        # 6a. Asymmetric Choice (Accept is easy/direct, Reject is absent or buried in Preferences)
        if accept_btn and not reject_btn:
            findings.append({
                "pattern": "Asymmetric Cookie Consent",
                "severity": "Medium",
                "detection_method": "Rule-Based",
                "confidence": 0.88,
                "element_type": "cookie_banner",
                "description": (
                    "The cookie consent interface provides an immediate 'Accept' option "
                    f"('{accept_btn}') but omits an equally accessible 'Reject' option, "
                    "nudging users toward consenting to tracking."
                ),
                "evidence": [f"Accept Button: '{accept_btn}'", f"Reject Option: Absent or Hidden (Secondary menu: {manage_btn or 'None'})"],
                "rule_signals": ["cookie_asymmetric_choice"]
            })

        # 6b. Pre-selected Tracking Checkboxes
        non_essential_preselected = []
        for cb in preselected:
            if isinstance(cb, dict):
                if not cb.get("is_essential"):
                    non_essential_preselected.append(cb.get("label", "Tracking/Marketing"))
            elif isinstance(cb, str):
                non_essential_preselected.append(cb)
        if non_essential_preselected:
            findings.append({
                "pattern": "Pre-selected Tracking Checkboxes",
                "severity": "Medium",
                "detection_method": "Rule-Based",
                "confidence": 0.90,
                "element_type": "cookie_banner",
                "description": (
                    "Non-essential tracking or marketing cookie categories are pre-checked by default, "
                    "violating privacy-by-default standards."
                ),
                "evidence": [f"Pre-checked category: {label}" for label in non_essential_preselected],
                "rule_signals": ["cookie_preselected_categories"]
            })

        # 6c. Cookie Wall / Obstruction (No close button and no reject button)
        if not reject_btn and not cookie_data.get("has_close_button") and not manage_btn:
            findings.append({
                "pattern": "Forced Cookie Wall",
                "severity": "High",
                "detection_method": "Rule-Based",
                "confidence": 0.85,
                "element_type": "cookie_banner",
                "description": (
                    "The site presents a mandatory consent dialog without an option to reject "
                    "or dismiss, compelling acceptance to proceed."
                ),
                "evidence": [f"Banner text: {banner_text[:120]}..."],
                "rule_signals": ["cookie_wall_blocking"]
            })

    return {
        "total_dark_patterns": len(findings),
        "findings": findings
    }


def detect_dark_patterns(scraped_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Complete Hybrid Dark Pattern Detection Pipeline:
    1. Runs Rule-Based Pattern Matcher.
    2. Runs Calibrated Supervised ML Models on Candidate DOM Elements.
    3. Fuses signals into consolidated findings (AI Model, Rule-Based, Hybrid).
    4. Calculates separate, explainable Dark Pattern Risk Score & Risk Level.
    5. Enriches findings with LLM Contextual Explanations (or grounded fallback).
    """
    # 1. Rule-Based Detector
    rule_results = detect_dark_patterns_rule_based(scraped_data)
    rule_findings = rule_results.get("findings", [])

    # 2. AI Detector
    ai_findings = []
    if ai_detector and ai_detector.is_ready():
        ai_res = ai_detector.analyze_page(scraped_data)
        ai_findings = ai_res.get("findings", [])

    # 3. Decision Fusion Logic
    fused_findings = []
    handled_ai_patterns = set()

    rule_to_ai_map = {
        "Urgency or Scarcity": ["Urgency", "Scarcity"],
        "Confirmshaming": ["Misdirection"],
        "Aggressive Call To Action": ["Forced Action", "Misdirection"],
    }

    for rf in rule_findings:
        rf_pattern = rf["pattern"]
        matched_ai_items = []
        target_ai_cats = rule_to_ai_map.get(rf_pattern, [])

        for af in ai_findings:
            if af["pattern"] in target_ai_cats or af["pattern"].lower() in rf_pattern.lower():
                matched_ai_items.append(af)
                handled_ai_patterns.add(af["pattern"])

        if matched_ai_items:
            # Signal Reinforcement: Both rules and ML flagged the pattern
            combined_evidence = list(rf["evidence"])
            highest_conf = rf.get("confidence", 0.85)
            element_type = rf.get("element_type", "text_block")

            for mai in matched_ai_items:
                for ev in mai.get("evidence", []):
                    if ev not in combined_evidence:
                        combined_evidence.append(ev)
                if mai.get("highest_confidence", 0) > highest_conf:
                    highest_conf = mai["highest_confidence"]
                    element_type = mai.get("element_type", element_type)

            # Boost confidence slightly due to dual confirmation, capped at 0.999
            reinforced_conf = min(0.999, round(highest_conf + 0.03, 4))

            fused_findings.append({
                "pattern": rf_pattern,
                "severity": rf["severity"] if rf["severity"] == "High" else "Medium",
                "detection_method": "Hybrid (Rules + AI)",
                "confidence": reinforced_conf,
                "element_type": element_type,
                "description": rf["description"],
                "evidence": combined_evidence,
                "rule_signals": rf.get("rule_signals", [])
            })
        else:
            # Uncorroborated Rule-Based signal
            fused_findings.append(rf)

    # 4. Add AI findings not captured by rules (e.g. Social Proof, Obstruction, Sneaking)
    for af in ai_findings:
        if af["pattern"] not in handled_ai_patterns:
            fused_findings.append({
                "pattern": af["pattern"],
                "severity": af["severity"],
                "detection_method": "AI Model",
                "confidence": round(af.get("highest_confidence", 0.90), 4),
                "element_type": af.get("element_type", "text_block"),
                "description": af["description"],
                "evidence": af.get("evidence", []),
                "rule_signals": []
            })

    # 5. Semantic Dark Pattern Risk Score
    risk_data = calculate_dark_pattern_risk(fused_findings, scraped_data)

    # 6. Enrich Findings with LLM Contextual Explanations
    enriched_findings, llm_status = enrich_findings_with_llm(fused_findings)

    # 7. Screenshot-Based Vision AI Analysis (Layout & Visual Prominence)
    screenshot_b64 = scraped_data.get("screenshot_b64")
    visual_analysis = analyze_screenshot(
        screenshot_b64,
        dom_context={
            "url": scraped_data.get("url", ""),
            "title": scraped_data.get("title", ""),
            "buttons": scraped_data.get("buttons", []),
            "dom_elements": scraped_data.get("dom_elements", [])
        }
    )

    # 8. Multi-Modal Decision Fusion (Corroborate DOM/Text + Screenshot Vision)
    multimodal_data = calculate_multimodal_risk(enriched_findings, visual_analysis, scraped_data)

    # Calculate average AI confidence across combined findings
    combined_findings = multimodal_data.get("combined_findings", enriched_findings)
    conf_values = [f.get("confidence", 0) for f in combined_findings if f.get("confidence")]
    avg_confidence = round(sum(conf_values) / len(conf_values), 4) if conf_values else 0.0

    # Model metadata
    model_meta = ai_detector.get_model_metadata() if (ai_detector and hasattr(ai_detector, "get_model_metadata")) else {}
    model_version = model_meta.get("model_version", "v2")
    model_name = model_meta.get("model_name", "Calibrated Linear SVM V2")
    test_acc = model_meta.get("test_accuracy", 0.9689)
    f1_sc = model_meta.get("f1_score", 0.9691)
    precision = model_meta.get("precision", 0.9672)
    recall = model_meta.get("recall", 0.9710)
    roc_auc = model_meta.get("roc_auc", 0.9924)
    acc_disp = model_meta.get("accuracy_display", f"{round(test_acc * 100, 2)}%")

    return {
        "risk_score": multimodal_data["combined_risk_score"],
        "risk_level": multimodal_data["combined_risk_level"],
        "risk_breakdown": multimodal_data.get("risk_breakdown", risk_data.get("risk_breakdown", {})),
        "total_dark_patterns": len(combined_findings),
        "findings": combined_findings,
        "score_breakdown": multimodal_data.get("score_breakdown", risk_data.get("score_breakdown", [])),
        "scoring_methodology": multimodal_data.get("methodology", risk_data.get("methodology", "")),
        "cookie_consent": scraped_data.get("cookie_consent", {}),
        "semantic_analysis": {
            "risk_score": risk_data["risk_score"],
            "risk_level": risk_data["risk_level"],
            "risk_breakdown": risk_data.get("risk_breakdown", {}),
            "total_patterns": len(enriched_findings),
            "findings": enriched_findings
        },
        "visual_analysis": visual_analysis,
        "combined_analysis": multimodal_data,
        "ai_analysis": {
            "model": model_name,
            "model_name": model_name,
            "model_version": model_version,
            "test_accuracy": test_acc,
            "precision": precision,
            "recall": recall,
            "f1_score": f1_sc,
            "roc_auc": roc_auc,
            "accuracy_display": acc_disp,
            "vision_model": visual_analysis.get("provider", "Vision AI Offline Fallback"),
            "average_confidence": avg_confidence,
            "llm_status": llm_status,
            "vision_status": visual_analysis.get("status", get_vision_status()),
            "v1_historical": model_meta.get("v1_historical")
        }
    }
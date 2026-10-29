"""
DarkShield AI - Website-Level Deceptive Risk Scoring Methodology
=================================================================

Computes an explainable, normalized Website-Level Deceptive Risk Score (0-100)
and corresponding Risk Level (None, Low, Medium, High, Very High).

Core 5-Factor Formulation:
    Risk Score = 25% Severity + 20% Confidence + 15% Frequency + 25% User Impact + 15% Behavioral Evidence

Factors (each normalized to 0-100):
1. Severity (25%):
   Evaluates harmfulness/deception of detected patterns.
   Blends peak severity (70%) with average severity (30%).
2. Confidence (20%):
   Detection certainty from SVM, Rules, and Vision AI.
   Weighted by pattern severity and reinforced by multi-modal corroboration.
3. Frequency (15%):
   Deduplicated count of distinct suspicious/deceptive elements.
   Mapped to a saturating 0-100 curve to prevent duplicate inflation.
4. User Impact (25%):
   Degree of decision-autonomy manipulation (forced actions, difficult opt-outs, confirmshaming).
   Blends peak impact (65%) with breadth of manipulative tactics (35%).
5. Behavioral Evidence (15%):
   Verified manipulative defaults (pre-checked tracking, absent reject button, hidden opt-out).
   Evaluates to 0 if no observable behavioral manipulation is present (no invented evidence).

Risk Level Thresholds:
- 0: None (No deceptive design patterns detected)
- 1 - 29: Low (Minor persuasive triggers or low confidence)
- 30 - 59: Medium (Notable manipulative patterns present)
- 60 - 79: High (Aggressive, multi-layered deceptive design)
- 80 - 100: Very High (Systemic manipulation, forced actions, or behavioral tricks)
"""

import math
from typing import List, Dict, Any, Optional


SEVERITY_SCALE = {
    "Critical": 100.0,
    "High": 75.0,
    "Medium": 50.0,
    "Low": 25.0,
    "Info": 10.0
}

SEVERITY_WEIGHTS = {
    "Critical": 30.0,
    "High": 22.0,
    "Medium": 14.0,
    "Low": 7.0,
    "Info": 2.0
}

METHOD_MULTIPLIERS = {
    "Multi-Modal (DOM + Vision + Rules)": 1.25,
    "Multi-Modal (DOM + Vision)": 1.20,
    "Hybrid (Rules + AI)": 1.15,
    "AI Model": 1.00,
    "Vision AI": 1.00,
    "Vision AI (Visual Layout)": 1.00,
    "Rule-Based": 0.90,
    "Rule-Based Pattern Matcher": 0.90
}

USER_IMPACT_WEIGHTS = {
    "forced action": 95.0,
    "forced registration": 90.0,
    "sneaking": 95.0,
    "hidden costs": 95.0,
    "obstruction": 90.0,
    "difficult rejection": 90.0,
    "roach motel": 90.0,
    "pre-selected": 85.0,
    "pre-selected tracking": 85.0,
    "pre-selected option": 85.0,
    "confirmshaming": 80.0,
    "misdirection": 75.0,
    "misleading cta": 75.0,
    "asymmetric": 75.0,
    "urgency": 70.0,
    "countdown": 70.0,
    "scarcity": 65.0,
    "social proof": 55.0,
    "aggressive cta": 50.0
}


def calculate_severity_score(findings: List[Dict[str, Any]]) -> float:
    """
    Calculate normalized Severity score (0-100).
    Blends peak severity (70%) with average severity (30%).
    """
    if not findings:
        return 0.0

    sev_values = [
        SEVERITY_SCALE.get(f.get("severity", "Medium"), 50.0)
        for f in findings
    ]
    max_sev = max(sev_values)
    avg_sev = sum(sev_values) / len(sev_values)
    return round(min(100.0, 0.70 * max_sev + 0.30 * avg_sev), 1)


def calculate_confidence_score(findings: List[Dict[str, Any]]) -> float:
    """
    Calculate normalized Confidence score (0-100).
    Computes severity-weighted average detection confidence across findings.
    """
    if not findings:
        return 0.0

    total_weight = 0.0
    weighted_conf = 0.0

    for f in findings:
        conf = float(f.get("confidence", 0.85))
        conf = max(0.0, min(1.0, conf))
        sev = f.get("severity", "Medium")
        w = SEVERITY_WEIGHTS.get(sev, 14.0)

        total_weight += w
        weighted_conf += conf * w

    if total_weight <= 0:
        return 0.0

    return round(min(100.0, (weighted_conf / total_weight) * 100.0), 1)


def calculate_frequency_score(findings: List[Dict[str, Any]]) -> float:
    """
    Calculate normalized Frequency score (0-100) based on distinct deceptive instances.
    Deduplicates findings by signature (pattern category + evidence summary) to avoid
    counting duplicate signals, then maps count to a saturating 0-100 curve.
    """
    if not findings:
        return 0.0

    seen_signatures = set()
    distinct_count = 0

    for f in findings:
        pat = (f.get("pattern") or "").lower().strip()
        ev = f.get("evidence", [])
        if isinstance(ev, list) and ev:
            ev_str = str(ev[0])[:60].lower().strip()
        elif isinstance(ev, str):
            ev_str = ev[:60].lower().strip()
        else:
            ev_str = ""

        sig = f"{pat}::{ev_str}"
        if sig not in seen_signatures:
            seen_signatures.add(sig)
            distinct_count += 1

    if distinct_count == 0:
        return 0.0

    # Saturating exponential: M=1 -> 31.6, M=2 -> 53.2, M=4 -> 78.1, M=7 -> 93.0
    score = 100.0 * (1.0 - math.exp(-0.38 * distinct_count))
    return round(min(100.0, score), 1)


def calculate_user_impact_score(findings: List[Dict[str, Any]]) -> float:
    """
    Calculate normalized User Impact score (0-100).
    Estimates the degree to which detected patterns manipulate decision autonomy.
    Blends maximum impact (65%) with average impact (35%).
    """
    if not findings:
        return 0.0

    impact_values = []
    for f in findings:
        pat = (f.get("pattern") or "").lower()
        matched_impact = None
        for key, weight in USER_IMPACT_WEIGHTS.items():
            if key in pat:
                matched_impact = weight
                break
        if matched_impact is None:
            matched_impact = SEVERITY_SCALE.get(f.get("severity", "Medium"), 50.0)
        impact_values.append(matched_impact)

    max_impact = max(impact_values)
    avg_impact = sum(impact_values) / len(impact_values)
    return round(min(100.0, 0.65 * max_impact + 0.35 * avg_impact), 1)


def calculate_behavioral_evidence_score(
    findings: List[Dict[str, Any]],
    website_data: Optional[Dict[str, Any]] = None
) -> float:
    """
    Calculate normalized Behavioral Evidence score (0-100).
    Evaluates verified behavioral manipulation (pre-selected defaults, difficult opt-outs,
    asymmetric actions, hidden elements).
    Returns 0.0 if no observable behavioral manipulation is present.
    """
    if not findings and not website_data:
        return 0.0

    behavioral_points = 0.0
    triggered_signals = set()

    # 1. Inspect direct findings for behavioral indicators
    for f in findings:
        pat = (f.get("pattern") or "").lower()
        rules = f.get("rule_signals", [])
        desc = (f.get("description") or "").lower()
        ev_str = " ".join([str(e) for e in f.get("evidence", [])]).lower()

        # Pre-selected tracking / consent
        if any(sig in rules for sig in ["cookie_preselected_categories", "preselected_checkbox_or_radio"]) or \
           "pre-selected" in pat or "pre-selected" in desc or "pre-checked" in ev_str:
            if "preselected" not in triggered_signals:
                behavioral_points += 35.0
                triggered_signals.add("preselected")

        # Asymmetric choice / difficult rejection
        if "cookie_asymmetric_choice" in rules or "asymmetric" in pat or "difficult rejection" in pat or \
           "absent or hidden" in ev_str or "subordinated opt-out" in pat:
            if "asymmetric_rejection" not in triggered_signals:
                behavioral_points += 30.0
                triggered_signals.add("asymmetric_rejection")

        # Hidden subscription / forced action
        if "sneaking_hidden_subscription" in rules or "forced" in pat or "roach motel" in pat:
            if "forced_hidden" not in triggered_signals:
                behavioral_points += 30.0
                triggered_signals.add("forced_hidden")

        # Visual layout asymmetry verified by Vision AI
        if "visual_corroboration" in f or "Vision AI" in f.get("detection_method", ""):
            v_det = (f.get("description") or "").lower()
            if any(term in v_det for term in ["asymmetric", "hidden", "contrast", "reduced", "buried"]):
                if "visual_asymmetry" not in triggered_signals:
                    behavioral_points += 25.0
                    triggered_signals.add("visual_asymmetry")

    # 2. Inspect website_data / cookie_consent if provided
    if website_data:
        cookie_data = website_data.get("cookie_consent", {})
        if cookie_data.get("banner_detected"):
            accept_btn = cookie_data.get("accept_button")
            reject_btn = cookie_data.get("reject_button")
            preselected = cookie_data.get("preselected_checkboxes", [])

            if preselected and "preselected" not in triggered_signals:
                behavioral_points += 35.0
                triggered_signals.add("preselected")

            if accept_btn and not reject_btn and "asymmetric_rejection" not in triggered_signals:
                behavioral_points += 30.0
                triggered_signals.add("asymmetric_rejection")

    return round(min(100.0, behavioral_points), 1)


def calculate_overall_risk_score(
    findings: List[Dict[str, Any]],
    website_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Calculate explainable website-level deceptive risk score from the 5 normalized factors:
        Risk Score = 25% Severity + 20% Confidence + 15% Frequency + 25% User Impact + 15% Behavioral Evidence
    """
    if not findings:
        return {
            "risk_score": 0,
            "risk_level": "None",
            "risk_breakdown": {
                "severity": 0.0,
                "confidence": 0.0,
                "frequency": 0.0,
                "user_impact": 0.0,
                "behavioral_evidence": 0.0
            },
            "score_breakdown": [],
            "methodology": "Score is 0 because no deceptive design patterns were detected."
        }

    severity_score = calculate_severity_score(findings)
    confidence_score = calculate_confidence_score(findings)
    frequency_score = calculate_frequency_score(findings)
    user_impact_score = calculate_user_impact_score(findings)
    behavioral_evidence_score = calculate_behavioral_evidence_score(findings, website_data)

    weighted_sum = (
        0.25 * severity_score +
        0.20 * confidence_score +
        0.15 * frequency_score +
        0.25 * user_impact_score +
        0.15 * behavioral_evidence_score
    )

    final_score = int(min(100, max(0, round(weighted_sum))))

    # Risk Levels:
    # 0: None (if 0 findings)
    # 1 - 29: Low
    # 30 - 59: Medium
    # 60 - 79: High
    # 80 - 100: Very High
    if final_score == 0 and not findings:
        risk_level = "None"
    elif final_score < 30:
        risk_level = "Low"
    elif final_score < 60:
        risk_level = "Medium"
    elif final_score < 80:
        risk_level = "High"
    else:
        risk_level = "Very High"

    # Construct backwards-compatible itemized score breakdown
    score_breakdown = []
    for f in findings:
        sev = f.get("severity", "Medium")
        bw = SEVERITY_WEIGHTS.get(sev, 14.0)
        c = float(f.get("confidence", 0.85))
        m = f.get("detection_method", "AI Model")
        mult = METHOD_MULTIPLIERS.get(m, 1.0)
        score_breakdown.append({
            "pattern": f.get("pattern", "Unknown Pattern"),
            "severity": sev,
            "base_weight": bw,
            "confidence": c,
            "method": m,
            "multiplier": mult,
            "points_contributed": round(bw * c * mult, 2)
        })

    methodology = (
        f"Website-level deceptive risk calculated from {len(findings)} pattern(s): "
        f"25% Severity ({severity_score:.1f}) + 20% Confidence ({confidence_score:.1f}) + "
        f"15% Frequency ({frequency_score:.1f}) + 25% User Impact ({user_impact_score:.1f}) + "
        f"15% Behavioral Evidence ({behavioral_evidence_score:.1f}) = {final_score}/100 ({risk_level} Risk)."
    )

    return {
        "risk_score": final_score,
        "risk_level": risk_level,
        "risk_breakdown": {
            "severity": severity_score,
            "confidence": confidence_score,
            "frequency": frequency_score,
            "user_impact": user_impact_score,
            "behavioral_evidence": behavioral_evidence_score
        },
        "score_breakdown": score_breakdown,
        "methodology": methodology
    }


def calculate_dark_pattern_risk(
    findings: List[Dict[str, Any]],
    website_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Calculate an explainable Dark Pattern Risk Score and Risk Level from detected patterns
    using the normalized 5-factor website-level methodology.
    """
    return calculate_overall_risk_score(findings, website_data)


def fuse_multimodal_findings(
    semantic_findings: List[Dict[str, Any]],
    visual_analysis: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Fuse semantic (DOM/Text) findings and visual (Screenshot Vision) findings.

    Principles:
    1. Multi-Modal Corroboration:
       If a pattern is detected by both semantic text analysis and vision layout analysis
       (e.g., Urgency text corroborated by a high-contrast visual countdown banner),
       method is elevated to 'Multi-Modal (DOM + Vision + Rules)' or 'Multi-Modal (DOM + Vision)'.
       Evidence is unified, and confidence is reinforced.
    2. Modality Independence:
       Patterns detected purely in text (e.g. subtle Social Proof) or purely in visual layout
       (e.g. Asymmetric button styling, disguised navigation) are preserved with their respective
       provenance and method identifiers.
    3. Non-destructive:
       Does not drop or alter existing semantic findings if Vision is unconfigured or returns 0 patterns.
    """
    if not visual_analysis or not visual_analysis.get("patterns"):
        return list(semantic_findings)

    visual_patterns = visual_analysis.get("patterns", [])
    combined = []
    matched_visual_indices = set()

    # Correlation dictionary between semantic categories and visual pattern concepts
    correlation_map = {
        "urgency": ["urgency", "countdown", "timer", "expir"],
        "scarcity": ["scarcity", "stock", "limited", "demand"],
        "misdirection": ["asymmetric", "button", "misdirection", "contrast", "color", "confirmshaming"],
        "confirmshaming": ["confirmshaming", "asymmetric", "opt-out", "decline"],
        "forced action": ["forced", "wall", "gate", "mandatory"],
        "sneaking": ["sneaking", "hidden", "obscured", "disclosure", "subscription"],
        "social proof": ["social proof", "activity", "purchased", "viewing"]
    }

    for sf in semantic_findings:
        sf_name = (sf.get("pattern") or "").lower()
        matched_vps = []

        # Find matching visual patterns
        for v_idx, vp in enumerate(visual_patterns):
            vp_name = (vp.get("name") or "").lower()
            is_match = False

            if vp_name in sf_name or sf_name in vp_name:
                is_match = True
            else:
                for sem_key, vis_keywords in correlation_map.items():
                    if sem_key in sf_name:
                        if any(kw in vp_name for kw in vis_keywords):
                            is_match = True
                            break

            if is_match:
                matched_vps.append((v_idx, vp))
                matched_visual_indices.add(v_idx)

        if matched_vps:
            base_method = sf.get("detection_method", "AI Model")
            if "Rules" in base_method:
                multimodal_method = "Multi-Modal (DOM + Vision + Rules)"
            else:
                multimodal_method = "Multi-Modal (DOM + Vision)"

            c_sem = float(sf.get("confidence", 0.85))
            c_vis = max([float(vp.get("confidence", 0.85)) for _, vp in matched_vps])
            reinforced_conf = min(0.999, round(1.0 - (1.0 - c_sem) * (1.0 - c_vis * 0.7), 4))

            combined_evidence = list(sf.get("evidence", []))
            visual_evidence_items = []
            for _, vp in matched_vps:
                v_ev = vp.get("evidence")
                v_det = vp.get("visual_details")
                if v_ev and v_ev not in combined_evidence:
                    visual_evidence_items.append(f"[Visual Evidence] {v_ev}")
                if v_det and v_det not in combined_evidence:
                    visual_evidence_items.append(f"[Layout Analysis] {v_det}")

            merged_finding = dict(sf)
            merged_finding["detection_method"] = multimodal_method
            merged_finding["confidence"] = reinforced_conf
            merged_finding["evidence"] = combined_evidence + visual_evidence_items
            merged_finding["visual_corroboration"] = {
                "visual_patterns": [vp.get("name") for _, vp in matched_vps],
                "visual_confidence": c_vis,
                "layout_details": [vp.get("visual_details") for _, vp in matched_vps if vp.get("visual_details")]
            }
            combined.append(merged_finding)
        else:
            combined.append(dict(sf))

    # Add unmatched visual patterns (pure layout asymmetry, disguised buttons, etc.)
    for v_idx, vp in enumerate(visual_patterns):
        if v_idx not in matched_visual_indices:
            v_name = vp.get("name", "Visual Dark Pattern")
            v_ev = vp.get("evidence", "")
            v_det = vp.get("visual_details", "")
            evidence_list = []
            if v_ev:
                evidence_list.append(f"[Visual Evidence] {v_ev}")
            if v_det:
                evidence_list.append(f"[Layout Analysis] {v_det}")

            combined.append({
                "pattern": v_name,
                "severity": vp.get("severity", "Medium"),
                "detection_method": "Vision AI (Visual Layout)",
                "confidence": round(float(vp.get("confidence", 0.85)), 4),
                "element_type": "visual_layout",
                "description": vp.get("visual_details") or f"Visual deceptive presentation: {v_name}",
                "evidence": evidence_list,
                "explanation": vp.get("visual_details") or "Deceptive visual hierarchy detected via screenshot analysis.",
                "why_it_matters": "Visual asymmetry and layout tricks manipulate visual attention and induce unintended user choices.",
                "recommendation": vp.get("recommendation", "Examine interface options carefully regardless of button colors or size hierarchy.")
            })

    return combined


def calculate_multimodal_risk(
    semantic_findings: List[Dict[str, Any]],
    visual_analysis: Dict[str, Any],
    website_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Calculate consolidated multi-modal risk score and findings using the 5-factor model.
    """
    fused_findings = fuse_multimodal_findings(semantic_findings, visual_analysis)
    risk_data = calculate_dark_pattern_risk(fused_findings, website_data)

    corroborated_count = sum(1 for f in fused_findings if "Multi-Modal" in f.get("detection_method", ""))
    visual_only_count = sum(1 for f in fused_findings if "Vision AI" in f.get("detection_method", ""))
    semantic_only_count = len(fused_findings) - corroborated_count - visual_only_count

    fusion_summary = (
        f"Multi-modal fusion synthesized {len(fused_findings)} total findings "
        f"({corroborated_count} corroborated by DOM+Vision, {semantic_only_count} semantic DOM/Text, "
        f"{visual_only_count} visual layout)."
    )

    return {
        "combined_risk_score": risk_data["risk_score"],
        "combined_risk_level": risk_data["risk_level"],
        "combined_findings": fused_findings,
        "total_combined_patterns": len(fused_findings),
        "risk_breakdown": risk_data.get("risk_breakdown", {}),
        "score_breakdown": risk_data["score_breakdown"],
        "methodology": risk_data["methodology"],
        "fusion_summary": fusion_summary,
        "modality_breakdown": {
            "semantic_only_count": semantic_only_count,
            "visual_only_count": visual_only_count,
            "multimodal_corroborated_count": corroborated_count
        }
    }

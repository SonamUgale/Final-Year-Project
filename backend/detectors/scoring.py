"""
DarkShield AI - Dark Pattern Risk Scoring Methodology
======================================================

Computes an explainable, deterministic Dark Pattern Risk Score (0-100)
and corresponding Risk Level (None, Low, Medium, High).

Scoring Principles:
1. Complete Separation: Kept entirely distinct from the security vulnerability score.
2. Severity-Weighted: Higher deception severity (Sneaking, Forced Action, Obstruction)
   contributes more points than persuasive triggers (Urgency, Scarcity, CTA).
3. Confidence-Scaled: Each pattern's contribution is scaled by the ML/Hybrid confidence.
4. Certainty-Boost: Hybrid detections (confirmed by both rules and ML) receive a 1.15x
   certainty multiplier.
5. Explainability: Every score calculation includes an itemized breakdown of contributing factors.

Formulas:
- Pattern Contribution = Base Weight * Confidence * Method Multiplier
- Base Weights:
  * Critical = 30 pts (Forced Action, Sneaking Hidden Charges)
  * High     = 22 pts (Obstruction, Severe Misdirection, Confirmed Confirmshaming)
  * Medium   = 14 pts (Urgency, Scarcity, Social Proof)
  * Low      = 7 pts  (Aggressive CTA, Excessive External Links)
- Total Risk Score = min(100, round(sum(Pattern Contributions)))

Risk Level Thresholds:
- 0: None (No deceptive design patterns detected)
- 1 - 24: Low (Minor persuasive triggers or low confidence)
- 25 - 59: Medium (Notable manipulative patterns present)
- 60 - 100: High (Aggressive, multi-layered deceptive design)
"""

from typing import List, Dict, Any


SEVERITY_WEIGHTS = {
    "Critical": 30.0,
    "High": 22.0,
    "Medium": 14.0,
    "Low": 7.0,
    "Info": 2.0
}

METHOD_MULTIPLIERS = {
    "Hybrid (Rules + AI)": 1.15,
    "AI Model": 1.00,
    "Rule-Based": 0.90,
    "Rule-Based Pattern Matcher": 0.90
}


def calculate_dark_pattern_risk(findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate an explainable Dark Pattern Risk Score and Risk Level from detected patterns.
    """
    if not findings:
        return {
            "risk_score": 0,
            "risk_level": "None",
            "score_breakdown": [],
            "methodology": "Score is 0 because no deceptive design patterns were detected."
        }

    breakdown = []
    raw_score = 0.0

    for finding in findings:
        severity = finding.get("severity", "Medium")
        base_weight = SEVERITY_WEIGHTS.get(severity, 14.0)
        
        confidence = float(finding.get("confidence", 0.85))
        method = finding.get("detection_method", "AI Model")
        multiplier = METHOD_MULTIPLIERS.get(method, 1.0)
        
        pattern_name = finding.get("pattern", "Unknown Pattern")
        contribution = round(base_weight * confidence * multiplier, 2)
        raw_score += contribution

        breakdown.append({
            "pattern": pattern_name,
            "severity": severity,
            "base_weight": base_weight,
            "confidence": confidence,
            "method": method,
            "multiplier": multiplier,
            "points_contributed": contribution
        })

    final_score = int(min(100, round(raw_score)))

    # Determine risk level
    if final_score == 0:
        risk_level = "None"
    elif final_score < 25:
        risk_level = "Low"
    elif final_score < 60:
        risk_level = "Medium"
    else:
        risk_level = "High"

    # Critical patterns with high confidence elevate to at least Medium or High
    has_critical = any(f.get("severity") in ("Critical", "High") and float(f.get("confidence", 0)) >= 0.85 for f in findings)
    if has_critical and risk_level in ("None", "Low"):
        risk_level = "Medium"

    return {
        "risk_score": final_score,
        "risk_level": risk_level,
        "score_breakdown": breakdown,
        "methodology": (
            f"Calculated from {len(findings)} detected pattern(s) weighted by severity and "
            f"confidence (sum of contributions = {raw_score:.1f}, capped at 100)."
        )
    }

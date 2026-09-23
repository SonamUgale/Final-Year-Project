"""
DarkShield AI - LLM Findings Enricher
======================================

Enriches ML & hybrid detections with contextual explanations, impacts, and
recommendations using the active LLM provider (or grounded fallback).
"""

from typing import List, Dict, Any, Tuple
from backend.ai.llm.factory import get_llm_provider


def enrich_findings_with_llm(findings: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], str]:
    """
    Takes detected dark pattern findings and enriches each item with
    'explanation', 'why_it_matters', and 'recommendation'.
    
    Returns:
        (enriched_findings, llm_status)
    """
    provider, status = get_llm_provider()

    enriched = []
    for finding in findings:
        item = dict(finding)
        pattern = item.get("pattern", "Unknown Pattern")
        confidence = float(item.get("confidence", 0.85))
        evidence = item.get("evidence", [])
        if isinstance(evidence, str):
            evidence = [evidence]
            
        element_type = item.get("element_type", "web_element")
        context = item.get("context", "")
        rule_signals = item.get("rule_signals", [])

        # Call provider
        explanation_data = provider.explain_detection(
            pattern=pattern,
            confidence=confidence,
            evidence=evidence,
            element_type=element_type,
            context=context,
            rule_signals=rule_signals
        )

        item["explanation"] = explanation_data.get("explanation", item.get("description", ""))
        item["why_it_matters"] = explanation_data.get("why_it_matters", "Manipulative presentation impacts user autonomy.")
        item["recommendation"] = explanation_data.get("recommendation", "Review site terms and pricing carefully before purchasing.")

        enriched.append(item)

    return enriched, status

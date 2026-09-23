"""
DarkShield AI - LLM Contextual Analysis Package
================================================

Provides provider-agnostic contextual explanations for dark patterns
detected by the supervised ML model.
"""

from backend.ai.llm.factory import get_llm_provider, get_llm_status
from backend.ai.llm.explainer import enrich_findings_with_llm

__all__ = ["get_llm_provider", "get_llm_status", "enrich_findings_with_llm"]

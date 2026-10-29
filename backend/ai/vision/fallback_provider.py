"""
DarkShield AI - Offline Fallback Vision Provider
================================================

Provides safe, deterministic fallback responses when no external Vision AI
API key is configured. Ensures 100% uninterrupted operation without crashes.
"""

from typing import Dict, Any, Optional
from backend.ai.vision.base import BaseVisionProvider


class FallbackVisionProvider(BaseVisionProvider):
    """Fallback provider used when Vision API keys are unconfigured or offline."""

    @property
    def provider_name(self) -> str:
        return "Deterministic Grounded Vision Explainer (Offline Mode)"

    def is_available(self) -> bool:
        # Fallback is always ready to supply offline responses
        return False

    def analyze_screenshot(
        self,
        screenshot_b64: str,
        dom_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Return safe structured offline response indicating Vision AI is unconfigured."""
        return {
            "available": False,
            "detected": False,
            "visual_risk_score": 0,
            "visual_risk_level": "None",
            "visual_confidence": 0.0,
            "patterns": [],
            "analysis_summary": "Vision AI is optional and currently unconfigured. Set GEMINI_API_KEY or OPENAI_API_KEY to activate screenshot visual layout analysis.",
            "status": "Vision AI unavailable (API key not configured)"
        }

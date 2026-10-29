"""
DarkShield AI - Vision Inference & Detection Orchestrator
=========================================================

Coordinates screenshot preprocessing, provider invocation, schema validation,
and graceful fault tolerance for visual dark-pattern detection.
"""

import logging
from typing import Dict, Any, Optional

from backend.ai.vision.factory import get_vision_provider, get_vision_status

logger = logging.getLogger("darkshield.vision.detector")


class VisionDarkPatternDetector:
    """Singleton inference engine for screenshot-based visual dark pattern analysis."""

    _instance = None

    @classmethod
    def get_instance(cls) -> "VisionDarkPatternDetector":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def is_configured(self) -> bool:
        """Check whether an active Vision provider is available."""
        provider, _ = get_vision_provider()
        return provider.is_available()

    def analyze(
        self,
        screenshot_b64: Optional[str],
        dom_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute visual dark-pattern analysis on a screenshot.

        Fault-Tolerant Guarantees:
        - Never raises an unhandled exception to callers.
        - Returns structured schema even if screenshot is missing, empty, or unparseable.
        - Gracefully indicates offline/unconfigured status if no keys are set.
        """
        provider, status_str = get_vision_provider()

        # Check for empty screenshot
        if not screenshot_b64 or not isinstance(screenshot_b64, str) or len(screenshot_b64.strip()) < 50:
            return {
                "available": provider.is_available(),
                "status": "No screenshot available" if provider.is_available() else status_str,
                "detected": False,
                "visual_risk_score": 0,
                "visual_risk_level": "None",
                "visual_confidence": 0.0,
                "total_visual_patterns": 0,
                "patterns": [],
                "analysis_summary": "Screenshot was not captured or is empty; visual layout analysis skipped."
            }

        try:
            raw_result = provider.analyze_screenshot(screenshot_b64, dom_context)

            patterns = list(raw_result.get("patterns", []))
            score = int(raw_result.get("visual_risk_score", 0))
            score = max(0, min(100, score))

            # Derive risk level if omitted
            risk_level = raw_result.get("visual_risk_level")
            if not risk_level or risk_level == "None":
                if score >= 60:
                    risk_level = "High"
                elif score >= 25:
                    risk_level = "Medium"
                elif score > 0:
                    risk_level = "Low"
                else:
                    risk_level = "None"

            return {
                "available": raw_result.get("available", provider.is_available()),
                "status": raw_result.get("status", status_str),
                "detected": bool(raw_result.get("detected", len(patterns) > 0)),
                "visual_risk_score": score,
                "visual_risk_level": risk_level,
                "visual_confidence": round(float(raw_result.get("visual_confidence", 0.85 if patterns else 0.0)), 4),
                "total_visual_patterns": len(patterns),
                "patterns": patterns,
                "analysis_summary": raw_result.get(
                    "analysis_summary",
                    f"Identified {len(patterns)} visual deceptive design pattern(s)." if patterns else "No deceptive visual design patterns identified."
                )
            }

        except Exception as err:
            logger.error(f"Vision detector execution error: {err}")
            return {
                "available": provider.is_available(),
                "status": f"Vision analysis error: {str(err)[:80]}",
                "detected": False,
                "visual_risk_score": 0,
                "visual_risk_level": "None",
                "visual_confidence": 0.0,
                "total_visual_patterns": 0,
                "patterns": [],
                "analysis_summary": "An error occurred during vision analysis. Semantic text analysis operated normally."
            }


def analyze_screenshot(
    screenshot_b64: Optional[str],
    dom_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Functional convenience entry point for visual screenshot analysis."""
    return VisionDarkPatternDetector.get_instance().analyze(screenshot_b64, dom_context)

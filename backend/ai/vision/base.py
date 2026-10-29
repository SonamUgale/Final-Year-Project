"""
DarkShield AI - Base Vision Provider Interface
==============================================

Abstract base class defining the provider contract for screenshot-based
visual dark pattern analysis.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseVisionProvider(ABC):
    """Abstract interface for screenshot visual dark pattern analysis providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the unique name and model identifier of this vision provider."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if credentials and dependencies are active and configured."""
        pass

    @abstractmethod
    def analyze_screenshot(
        self,
        screenshot_b64: str,
        dom_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze webpage screenshot for deceptive visual hierarchy and patterns.

        Args:
            screenshot_b64: Base64-encoded JPEG/PNG image data of the rendered webpage.
            dom_context: Optional dictionary containing text snippets or interactive elements.

        Returns:
            Dict containing:
                "detected": bool,
                "visual_risk_score": int (0-100),
                "visual_risk_level": str ("None", "Low", "Medium", "High"),
                "visual_confidence": float (0.0-1.0),
                "patterns": List[Dict[str, Any]],
                "analysis_summary": str
        """
        pass

"""
DarkShield AI - Base LLM Provider Interface
===========================================

Abstract base class defining the provider contract for contextual explanations.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class BaseLLMProvider(ABC):
    """Abstract interface for LLM contextual explanation providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the unique name of this LLM provider."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if credentials and dependencies are available."""
        pass

    @abstractmethod
    def explain_detection(
        self,
        pattern: str,
        confidence: float,
        evidence: List[str],
        element_type: str,
        context: Optional[str] = None,
        rule_signals: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        Generate contextual explanation strictly grounded in the detected evidence.
        
        Returns:
            dict containing:
                "explanation": str,
                "why_it_matters": str,
                "recommendation": str
        """
        pass

"""
DarkShield AI - LLM Provider Factory
=====================================

Inspects environment variables and returns the appropriate LLM provider.
Never hardcodes keys. Returns 'LLM unavailable' when no API keys are present.
"""

import os
from typing import Tuple

from backend.ai.llm.base import BaseLLMProvider
from backend.ai.llm.gemini_provider import GeminiProvider
from backend.ai.llm.openai_provider import OpenAIProvider
from backend.ai.llm.fallback_provider import FallbackGroundedExplainer


def get_llm_provider() -> Tuple[BaseLLMProvider, str]:
    """
    Returns (provider_instance, status_string).
    
    Status strings:
    - "Active: Google Gemini (gemini-1.5-flash)"
    - "Active: OpenAI (gpt-4o-mini)"
    - "LLM unavailable (API key not configured; using deterministic explainer)"
    """
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        provider = GeminiProvider()
        return provider, f"Active: {provider.provider_name}"

    if os.environ.get("OPENAI_API_KEY"):
        provider = OpenAIProvider()
        return provider, f"Active: {provider.provider_name}"

    # No external API keys found
    provider = FallbackGroundedExplainer()
    return provider, "LLM unavailable (API key not configured; using grounded explainer)"


def get_llm_status() -> str:
    """Convenience function returning current LLM availability status."""
    _, status = get_llm_provider()
    return status

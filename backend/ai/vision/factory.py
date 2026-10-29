"""
DarkShield AI - Vision Provider Factory
=======================================

Inspects environment configuration and returns the appropriate Vision AI provider.
Ensures zero hardcoded credentials and safe offline fallback.
"""

import os
from typing import Tuple

from backend.ai.vision.base import BaseVisionProvider
from backend.ai.vision.gemini_provider import GeminiVisionProvider
from backend.ai.vision.openai_provider import OpenAIVisionProvider
from backend.ai.vision.fallback_provider import FallbackVisionProvider


def get_vision_provider() -> Tuple[BaseVisionProvider, str]:
    """
    Returns (provider_instance, status_string).

    Status strings:
    - "Active: Google Gemini Vision (gemini-1.5-flash)"
    - "Active: OpenAI Vision (gpt-4o-mini)"
    - "Vision AI unavailable (API key not configured)"
    """
    pref = (os.environ.get("VISION_PROVIDER") or "").strip().lower()

    # Explicit preference handling
    if pref == "openai" and os.environ.get("OPENAI_API_KEY"):
        provider = OpenAIVisionProvider()
        return provider, f"Active: {provider.provider_name}"

    if pref in ["gemini", "google"] and (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        provider = GeminiVisionProvider()
        return provider, f"Active: {provider.provider_name}"

    # Default discovery order: Gemini first, then OpenAI
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        provider = GeminiVisionProvider()
        return provider, f"Active: {provider.provider_name}"

    if os.environ.get("OPENAI_API_KEY"):
        provider = OpenAIVisionProvider()
        return provider, f"Active: {provider.provider_name}"

    # Offline fallback
    fallback = FallbackVisionProvider()
    return fallback, "Vision AI unavailable (API key not configured)"


def get_vision_status() -> str:
    """Convenience function returning current Vision AI status."""
    _, status = get_vision_provider()
    return status

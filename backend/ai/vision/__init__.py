"""
DarkShield AI - Vision Analysis Module
======================================

Public exports for screenshot-based visual dark pattern analysis.
"""

from backend.ai.vision.base import BaseVisionProvider
from backend.ai.vision.factory import get_vision_provider, get_vision_status
from backend.ai.vision.vision_detector import (
    VisionDarkPatternDetector,
    analyze_screenshot,
)

__all__ = [
    "BaseVisionProvider",
    "get_vision_provider",
    "get_vision_status",
    "VisionDarkPatternDetector",
    "analyze_screenshot",
]

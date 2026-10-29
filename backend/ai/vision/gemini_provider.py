"""
DarkShield AI - Google Gemini Vision Provider
=============================================

Performs multimodal screenshot visual analysis using Google Gemini Vision (e.g. gemini-1.5-flash)
via standard urllib HTTP requests without requiring third-party SDKs.
"""

import os
import json
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

from backend.ai.vision.base import BaseVisionProvider
from backend.ai.vision.prompt import VISION_SYSTEM_PROMPT, build_vision_user_prompt
from backend.ai.vision.fallback_provider import FallbackVisionProvider

logger = logging.getLogger("darkshield.vision.gemini")


class GeminiVisionProvider(BaseVisionProvider):
    """Google Gemini multimodal screenshot analysis provider."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.model_name = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
        self._fallback = FallbackVisionProvider()

    @property
    def provider_name(self) -> str:
        return f"Google Gemini Vision ({self.model_name})"

    def is_available(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 0)

    def analyze_screenshot(
        self,
        screenshot_b64: str,
        dom_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send screenshot and optional DOM context to Gemini Vision."""
        if not self.is_available():
            return self._fallback.analyze_screenshot(screenshot_b64, dom_context)

        if not screenshot_b64 or len(screenshot_b64.strip()) < 50:
            logger.warning("Empty or invalid screenshot provided to Gemini Vision.")
            res = self._fallback.analyze_screenshot(screenshot_b64, dom_context)
            res["analysis_summary"] = "No valid screenshot available for visual analysis."
            return res

        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model_name}:generateContent?key={self.api_key}"
        )

        user_prompt = build_vision_user_prompt(dom_context)

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": user_prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": screenshot_b64.strip()
                            }
                        }
                    ]
                }
            ],
            "systemInstruction": {
                "parts": [
                    {"text": VISION_SYSTEM_PROMPT}
                ]
            },
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json"
            }
        }

        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                endpoint,
                data=req_data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=25) as resp:
                resp_json = json.loads(resp.read().decode("utf-8"))

            candidates = resp_json.get("candidates", [])
            if not candidates:
                logger.warning("Gemini Vision returned empty candidates list.")
                return self._fallback.analyze_screenshot(screenshot_b64, dom_context)

            raw_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            parsed = self._clean_and_parse_json(raw_text)

            return {
                "available": True,
                "provider": self.provider_name,
                "detected": bool(parsed.get("detected", False)),
                "visual_risk_score": int(parsed.get("visual_risk_score", 0)),
                "visual_risk_level": str(parsed.get("visual_risk_level", "None")),
                "visual_confidence": float(parsed.get("visual_confidence", 0.85)),
                "patterns": list(parsed.get("patterns", [])),
                "analysis_summary": str(parsed.get("analysis_summary", "")),
                "status": f"Active: {self.provider_name}"
            }

        except urllib.error.HTTPError as http_err:
            logger.error(f"Gemini Vision HTTP error {http_err.code}: {http_err.reason}")
            fallback_res = self._fallback.analyze_screenshot(screenshot_b64, dom_context)
            fallback_res["status"] = f"Vision AI failed (HTTP {http_err.code})"
            return fallback_res
        except Exception as e:
            logger.error(f"Gemini Vision unexpected error: {e}")
            fallback_res = self._fallback.analyze_screenshot(screenshot_b64, dom_context)
            fallback_res["status"] = "Vision AI failed (Network or parsing error)"
            return fallback_res

    def _clean_and_parse_json(self, raw_text: str) -> Dict[str, Any]:
        """Strip markdown fences and parse JSON robustly."""
        cleaned = raw_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except Exception:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end != -1:
                return json.loads(cleaned[start:end + 1])
            raise ValueError(f"Unable to parse JSON from vision response: {raw_text[:100]}...")

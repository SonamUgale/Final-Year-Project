"""
DarkShield AI - OpenAI Vision Provider
======================================

Performs multimodal screenshot visual analysis using OpenAI Vision (e.g. gpt-4o-mini)
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

logger = logging.getLogger("darkshield.vision.openai")


class OpenAIVisionProvider(BaseVisionProvider):
    """OpenAI multimodal screenshot analysis provider."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model_name = os.environ.get("OPENAI_VISION_MODEL", "gpt-4o-mini")
        self._fallback = FallbackVisionProvider()

    @property
    def provider_name(self) -> str:
        return f"OpenAI Vision ({self.model_name})"

    def is_available(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 0)

    def analyze_screenshot(
        self,
        screenshot_b64: str,
        dom_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send screenshot and optional DOM context to OpenAI Vision."""
        if not self.is_available():
            return self._fallback.analyze_screenshot(screenshot_b64, dom_context)

        if not screenshot_b64 or len(screenshot_b64.strip()) < 50:
            logger.warning("Empty or invalid screenshot provided to OpenAI Vision.")
            res = self._fallback.analyze_screenshot(screenshot_b64, dom_context)
            res["analysis_summary"] = "No valid screenshot available for visual analysis."
            return res

        endpoint = "https://api.openai.com/v1/chat/completions"
        user_prompt = build_vision_user_prompt(dom_context)

        # Build data URI
        clean_b64 = screenshot_b64.strip()
        data_uri = f"data:image/jpeg;base64,{clean_b64}"

        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": VISION_SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": data_uri,
                                "detail": "low"
                            }
                        }
                    ]
                }
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }

        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                endpoint,
                data=req_data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                },
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=25) as resp:
                resp_json = json.loads(resp.read().decode("utf-8"))

            choices = resp_json.get("choices", [])
            if not choices:
                logger.warning("OpenAI Vision returned empty choices list.")
                return self._fallback.analyze_screenshot(screenshot_b64, dom_context)

            raw_text = choices[0].get("message", {}).get("content", "")
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
            logger.error(f"OpenAI Vision HTTP error {http_err.code}: {http_err.reason}")
            fallback_res = self._fallback.analyze_screenshot(screenshot_b64, dom_context)
            fallback_res["status"] = f"Vision AI failed (HTTP {http_err.code})"
            return fallback_res
        except Exception as e:
            logger.error(f"OpenAI Vision unexpected error: {e}")
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

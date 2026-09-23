"""
DarkShield AI - Google Gemini LLM Provider
==========================================

Calls Google Gemini API to generate contextual explanations when
GEMINI_API_KEY or GOOGLE_API_KEY is configured in the environment.
"""

import os
import json
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional

from backend.ai.llm.base import BaseLLMProvider
from backend.ai.llm.fallback_provider import FallbackGroundedExplainer


class GeminiProvider(BaseLLMProvider):
    """Google Gemini contextual explanation provider."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.model_name = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
        self._fallback = FallbackGroundedExplainer()

    @property
    def provider_name(self) -> str:
        return f"Google Gemini ({self.model_name})"

    def is_available(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 0)

    def explain_detection(
        self,
        pattern: str,
        confidence: float,
        evidence: List[str],
        element_type: str,
        context: Optional[str] = None,
        rule_signals: Optional[List[str]] = None
    ) -> Dict[str, str]:
        if not self.is_available():
            return self._fallback.explain_detection(
                pattern, confidence, evidence, element_type, context, rule_signals
            )

        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"

        prompt = f"""You are an AI dark-pattern analysis expert. Analyze the following detected dark pattern from a website.
DO NOT invent evidence. Strictly ground your analysis in the provided evidence.

Detected Pattern: {pattern}
ML Confidence: {confidence * 100:.1f}%
Element Type: {element_type}
Evidence Text: {json.dumps(evidence)}
Surrounding DOM Context: {context or 'None'}
Supporting Rule Signals: {json.dumps(rule_signals or [])}

Respond ONLY with a valid JSON object with EXACTLY three keys:
{{
    "explanation": "Clear, objective explanation of how this specific evidence functions as a {pattern} dark pattern.",
    "why_it_matters": "The psychological impact or potential harm to the user's decision making.",
    "recommendation": "Concrete, actionable advice for a user viewing this webpage."
}}"""

        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json"
            }
        }

        try:
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text_out = data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(text_out)
                
                return {
                    "explanation": str(parsed.get("explanation", "")).strip(),
                    "why_it_matters": str(parsed.get("why_it_matters", "")).strip(),
                    "recommendation": str(parsed.get("recommendation", "")).strip()
                }
        except Exception as err:
            # Operational continuity: fall back to grounded explanation if API fails
            print(f"[GeminiProvider] API call failed ({err}), using grounded fallback.")
            return self._fallback.explain_detection(
                pattern, confidence, evidence, element_type, context, rule_signals
            )

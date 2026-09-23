"""
DarkShield AI - OpenAI LLM Provider
====================================

Calls OpenAI Chat Completions API to generate contextual explanations when
OPENAI_API_KEY is configured in the environment.
"""

import os
import json
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional

from backend.ai.llm.base import BaseLLMProvider
from backend.ai.llm.fallback_provider import FallbackGroundedExplainer


class OpenAIProvider(BaseLLMProvider):
    """OpenAI contextual explanation provider."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model_name = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        self._fallback = FallbackGroundedExplainer()

    @property
    def provider_name(self) -> str:
        return f"OpenAI ({self.model_name})"

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

        endpoint = "https://api.openai.com/v1/chat/completions"

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
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": "You are a professional dark-pattern consumer protection analyst."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"}
        }

        try:
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text_out = data["choices"][0]["message"]["content"]
                parsed = json.loads(text_out)
                
                return {
                    "explanation": str(parsed.get("explanation", "")).strip(),
                    "why_it_matters": str(parsed.get("why_it_matters", "")).strip(),
                    "recommendation": str(parsed.get("recommendation", "")).strip()
                }
        except Exception as err:
            print(f"[OpenAIProvider] API call failed ({err}), using grounded fallback.")
            return self._fallback.explain_detection(
                pattern, confidence, evidence, element_type, context, rule_signals
            )

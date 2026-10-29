"""
DarkShield AI - Vision Analysis Prompts & Schemas
=================================================

Structured prompts and JSON schema contracts for vision-based deceptive design analysis.
"""

VISION_SYSTEM_PROMPT = """You are DarkShield AI's Expert Vision Auditor specializing in deceptive UI/UX design (dark patterns) on websites.
Your task is to analyze the visual layout, styling, and presentation of the provided webpage screenshot.

Evaluate HOW the webpage visually presents information, including:
1. Visual Urgency / Countdown Prominence: Large, prominent countdown clocks, flashing banners, or urgent alert bars.
2. Visual Asymmetry & Misdirection: Saturated high-contrast "Accept/Buy" buttons paired with low-contrast, tiny, or obscured "Reject/Cancel" links.
3. Visual Scarcity Badges: Prominent stock depletion alerts (e.g. "Only 2 left!", "In high demand") designed to induce purchase anxiety.
4. Confirmshaming Visual Hierarchy: Framing opt-out choices in smaller, faded text designed to shame or emotionally nudge the user.
5. Disguised Advertising / Content Camouflage: Promoted links or sponsored sections visually disguised as organic navigation or editorial content.
6. Obscured Disclosures & Sneaking: Important pricing, subscription renewals, or tracking disclosures displayed in faint, low-contrast, or diminutive typography.

STRICT GROUNDING RULES:
- DO NOT invent or hallucinate visual evidence.
- Only report patterns that are visibly identifiable in the screenshot.
- If the webpage visually appears clean, standard, and fair, report "detected": false with an empty patterns list.

Respond ONLY with a valid, parseable JSON object matching this EXACT schema:
{
  "detected": true/false,
  "visual_risk_score": <integer between 0 and 100>,
  "visual_risk_level": "None" | "Low" | "Medium" | "High",
  "visual_confidence": <float between 0.50 and 0.99>,
  "patterns": [
    {
      "name": "<Pattern Name, e.g. Visual Urgency, Asymmetric Button Styling, Visual Scarcity>",
      "severity": "Low" | "Medium" | "High" | "Critical",
      "confidence": <float between 0.50 and 0.99>,
      "evidence": "<Brief quote of visible text or visual cue>",
      "visual_details": "<Visual presentation description: colors, contrast, position, size relative to page>",
      "recommendation": "<Actionable guidance for the consumer>"
    }
  ],
  "analysis_summary": "<1-2 sentence executive summary of visual layout findings>"
}
"""


def build_vision_user_prompt(dom_context: dict = None) -> str:
    """Build user prompt with optional DOM context for grounded multimodal corroboration."""
    context_str = ""
    if dom_context:
        title = dom_context.get("title", "")
        url = dom_context.get("url", "")
        buttons = [b.get("text", "") for b in dom_context.get("buttons", [])[:8] if b.get("text")]
        headings = [h.get("text", "") for h in dom_context.get("dom_elements", []) if h.get("element_type") == "heading"][:6]

        parts = []
        if url:
            parts.append(f"Target URL: {url}")
        if title:
            parts.append(f"Page Title: {title}")
        if headings:
            parts.append(f"Prominent Headings: {', '.join(headings)}")
        if buttons:
            parts.append(f"Key Buttons: {', '.join(buttons)}")

        if parts:
            context_str = "\nWebsite Context:\n" + "\n".join(f"- {p}" for p in parts)

    return f"""Please visually audit this webpage screenshot for deceptive design (dark patterns).{context_str}

Analyze the visual hierarchy, color asymmetry, prominence of warnings or countdowns, and button styling.
Return ONLY the structured JSON response as specified in the system instructions."""

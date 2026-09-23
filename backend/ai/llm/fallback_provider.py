"""
DarkShield AI - Grounded Rule/Category Fallback Explainer
=========================================================

Generates strictly grounded explanations when an external LLM API key is not configured.
Guarantees 100% operational continuity without crashing.
"""

from typing import Dict, Any, List, Optional
from backend.ai.llm.base import BaseLLMProvider


GROUNDED_EXPLANATION_TEMPLATES = {
    "Scarcity": {
        "explanation": (
            "The webpage displays statements claiming limited item availability or low stock counts. "
            "In e-commerce, such notices often artificially pressure shoppers into rapid purchases "
            "before verifying authenticity or comparing alternatives."
        ),
        "why_it_matters": (
            "Artificially induced scarcity restricts decision-making time, heightens fear of missing out (FOMO), "
            "and frequently leads to impulsive or unneeded financial commitments."
        ),
        "recommendation": (
            "Pause and evaluate whether you genuinely need the item. Cross-check availability on other platforms "
            "and do not let low-stock counters rush your purchasing decision."
        )
    },
    "Urgency": {
        "explanation": (
            "The interface employs countdown language or expiring deadline warnings to simulate time pressure. "
            "This tactic accelerates user action by making standard offers appear strictly momentary."
        ),
        "why_it_matters": (
            "Time pressure hinders rational evaluation of terms, return policies, and pricing, leading consumers "
            "to commit to transactions before fully reviewing details."
        ),
        "recommendation": (
            "Ignore ticking timers or expiring deal banners. Genuine deals are regularly repeated, and taking "
            "time to review all order details prevents unintended purchases."
        )
    },
    "Social Proof": {
        "explanation": (
            "The site highlights notifications of other users' recent activity (e.g., purchases, views, or cart additions). "
            "These messages simulate collective urgency and popular demand."
        ),
        "why_it_matters": (
            "Peer activity alerts exploit herd behavior to validate purchases without objective evidence of quality or necessity."
        ),
        "recommendation": (
            "Base your buying decision on independent product reviews and personal necessity rather than on-screen activity tickers."
        )
    },
    "Misdirection": {
        "explanation": (
            "The page utilizes asymmetric phrasing or confirmshaming where rejecting an offer is framed "
            "in humiliating or emotionally manipulative terms (e.g. 'No thanks, I prefer paying full price')."
        ),
        "why_it_matters": (
            "Confirmshaming preys on user psychology to induce guilt or self-doubt when exercising valid consumer choices like declining marketing opt-ins."
        ),
        "recommendation": (
            "Recognize the manipulative phrasing and confidently click the decline option. You are entitled to reject offers without feeling judged."
        )
    },
    "Obstruction": {
        "explanation": (
            "The interface creates unnecessary hurdles or complex friction when attempting to cancel, opt out, or modify selections."
        ),
        "why_it_matters": (
            "Intentional cancellation barriers make users abandon attempts to unsubscribe, leading to recurring unwanted charges."
        ),
        "recommendation": (
            "Document your attempt to cancel or opt out. Look for direct account settings or contact customer support immediately."
        )
    },
    "Sneaking": {
        "explanation": (
            "The interface conceals or quietly introduces additional charges, service fees, or opt-ins late in the workflow."
        ),
        "why_it_matters": (
            "Users may complete a transaction without realizing the final price exceeds what was initially displayed."
        ),
        "recommendation": (
            "Inspect line-item totals before finalizing checkout. Remove pre-selected add-ons or insurance checkboxes."
        )
    },
    "Forced Action": {
        "explanation": (
            "The site obligates the user to perform unrelated actions (such as joining a marketing list or sharing contact info) to complete a basic task."
        ),
        "why_it_matters": (
            "Forces relinquishment of privacy or consent without providing an equitable, unbundled alternative."
        ),
        "recommendation": (
            "Review privacy toggles. Decline non-essential marketing consents or seek services that respect unbundled consent."
        )
    },
    "Aggressive Call To Action": {
        "explanation": (
            "Interactive buttons on this page use forceful, urgent command verbs repeatedly to impel immediate action."
        ),
        "why_it_matters": (
            "Repetitive visual pressure distracts from reviewing full terms or alternative options."
        ),
        "recommendation": (
            "Take your time to explore the complete webpage before clicking high-emphasis action buttons."
        )
    },
    "Potential Forced Registration": {
        "explanation": (
            "The website requires immediate user account creation or sign-in before allowing access to standard information."
        ),
        "why_it_matters": (
            "Forces users into an account relationship and marketing funnel before building trust or providing value."
        ),
        "recommendation": (
            "Determine if account creation is genuinely necessary for your purpose, or look for guest checkout options."
        )
    },
    "Large Number of External Links": {
        "explanation": (
            "The page contains an unusually high number of links directing to third-party domains."
        ),
        "why_it_matters": (
            "May indicate affiliate stuffing, content scraping, or redirections to untrusted external destinations."
        ),
        "recommendation": (
            "Verify the destination domain in your browser's status bar before clicking external links."
        )
    }
}


class FallbackGroundedExplainer(BaseLLMProvider):
    """Provides deterministic, evidence-grounded explanations without external API dependency."""

    @property
    def provider_name(self) -> str:
        return "Deterministic Grounded Explainer"

    def is_available(self) -> bool:
        return True

    def explain_detection(
        self,
        pattern: str,
        confidence: float,
        evidence: List[str],
        element_type: str,
        context: Optional[str] = None,
        rule_signals: Optional[List[str]] = None
    ) -> Dict[str, str]:
        # Retrieve base template for pattern
        template = None
        for k, v in GROUNDED_EXPLANATION_TEMPLATES.items():
            if k.lower() in pattern.lower() or pattern.lower() in k.lower():
                template = v
                break

        if not template:
            template = {
                "explanation": f"The webpage content exhibits indicators consistent with {pattern}.",
                "why_it_matters": "Deceptive design patterns influence consumer autonomy and choices through manipulative presentation.",
                "recommendation": "Review the highlighted evidence carefully before taking any action on this website."
            }

        # Ground the explanation by directly incorporating specific evidence and element type
        evidence_preview = ", ".join(f'"{e}"' for e in evidence[:3]) if evidence else "detected interface elements"
        element_label = f" (found in {element_type})" if element_type and element_type != "unknown" else ""

        grounded_explanation = (
            f"{template['explanation']} Specifically, DarkShield AI identified the phrase(s) "
            f"{evidence_preview}{element_label} with an AI confidence of {confidence*100:.1f}%."
        )

        return {
            "explanation": grounded_explanation,
            "why_it_matters": template["why_it_matters"],
            "recommendation": template["recommendation"]
        }

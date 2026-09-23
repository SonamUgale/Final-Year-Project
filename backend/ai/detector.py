"""
DarkShield AI - Inference & Detection Engine
============================================

Provides fast, in-memory dark-pattern detection on scraped website content
using the trained Calibrated SVM and Multiclass Category models.

Key Capabilities:
- Multi-source candidate extraction (headings, buttons, links, labels, inputs, banners, paragraphs).
- Context preservation (surrounding text, element type, HTML tag).
- Stage 1: Binary prediction with calibrated probability score.
- Stage 2: Multiclass category classification for positive detections.
- Strict evidence fidelity (never invents text).
- Severity rating and descriptive explanations.
"""

import os
import re
import joblib
import numpy as np
from typing import List, Dict, Any

from backend.ai.preprocessing import clean_text


# -------------------------------------------------
# MODEL PATHS
# -------------------------------------------------

AI_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(AI_DIR, "models")

BINARY_VEC_PATH = os.path.join(MODELS_DIR, "binary_vectorizer.joblib")
BINARY_MODEL_PATH = os.path.join(MODELS_DIR, "binary_model.joblib")
CAT_VEC_PATH = os.path.join(MODELS_DIR, "category_vectorizer.joblib")
CAT_MODEL_PATH = os.path.join(MODELS_DIR, "category_model.joblib")
CAT_ENCODER_PATH = os.path.join(MODELS_DIR, "category_encoder.joblib")


# Category-specific descriptions and baseline severities
CATEGORY_METADATA = {
    "Scarcity": {
        "severity": "Medium",
        "description": "Artificially signals limited stock or availability to rush the user into purchasing."
    },
    "Urgency": {
        "severity": "Medium",
        "description": "Imposes artificial countdown timers or deadlines to induce purchase anxiety."
    },
    "Social Proof": {
        "severity": "Medium",
        "description": "Displays peer activity (e.g., '30 people bought this') to manufacture social pressure."
    },
    "Misdirection": {
        "severity": "Medium",
        "description": "Uses visual asymmetry or confirmshaming to nudge the user toward an undesirable choice."
    },
    "Obstruction": {
        "severity": "High",
        "description": "Makes it intentionally difficult or confusing to cancel, opt-out, or modify choices."
    },
    "Sneaking": {
        "severity": "High",
        "description": "Disguises or quietly slips additional charges, recurring subscriptions, or items into the transaction."
    },
    "Forced Action": {
        "severity": "High",
        "description": "Forces the user to perform unwanted actions (e.g. forced marketing opt-ins) to proceed."
    }
}


class AIDarkPatternDetector:
    """Inference engine for detecting dark patterns in text and web pages."""
    
    _instance = None
    
    def __init__(self):
        self.binary_vectorizer = None
        self.binary_model = None
        self.category_vectorizer = None
        self.category_model = None
        self.category_encoder = None
        self._is_loaded = False
        self.load_models()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def load_models(self):
        """Load trained models from disk if not already in memory."""
        if self._is_loaded:
            return

        required_files = [
            BINARY_VEC_PATH,
            BINARY_MODEL_PATH,
            CAT_VEC_PATH,
            CAT_MODEL_PATH,
            CAT_ENCODER_PATH
        ]
        
        for p in required_files:
            if not os.path.exists(p):
                print(f"[AIDarkPatternDetector] Warning: Model file not found at {p}. AI detection disabled.")
                return

        try:
            self.binary_vectorizer = joblib.load(BINARY_VEC_PATH)
            self.binary_model = joblib.load(BINARY_MODEL_PATH)
            self.category_vectorizer = joblib.load(CAT_VEC_PATH)
            self.category_model = joblib.load(CAT_MODEL_PATH)
            self.category_encoder = joblib.load(CAT_ENCODER_PATH)
            self._is_loaded = True
            print("[AIDarkPatternDetector] AI Models loaded successfully.")
        except Exception as e:
            print(f"[AIDarkPatternDetector] Error loading models: {e}")
            self._is_loaded = False

    def is_ready(self) -> bool:
        """Check if models are loaded and ready for inference."""
        return self._is_loaded

    def extract_candidates(self, scraped_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract candidate items from scraped data with metadata:
        - text: the text to evaluate
        - element_type: button | heading | link | label | input_placeholder | banner_or_dialog | text_block
        - context: surrounding text/parent element context
        - tag: HTML tag name
        """
        candidates = []
        seen_texts = set()

        # 1. Use pre-extracted dom_elements if present from browser.py
        dom_elements = scraped_data.get("dom_elements", [])
        if dom_elements:
            for item in dom_elements:
                raw_txt = item.get("text", "")
                txt_clean = clean_text(raw_txt)
                if txt_clean and len(txt_clean) >= 4 and txt_clean not in seen_texts:
                    seen_texts.add(txt_clean)
                    candidates.append({
                        "text": txt_clean,
                        "element_type": item.get("element_type", "dom_element"),
                        "tag": item.get("tag", ""),
                        "context": clean_text(item.get("context", ""))
                    })

        # 2. Extract from buttons if not already captured
        buttons = scraped_data.get("buttons", [])
        for btn in buttons:
            txt = clean_text(btn.get("text", ""))
            if txt and len(txt) >= 3 and txt not in seen_texts:
                seen_texts.add(txt)
                candidates.append({
                    "text": txt,
                    "element_type": "button",
                    "tag": "button",
                    "context": "Interactive button"
                })

        # 3. Extract from inputs (placeholders)
        inputs = scraped_data.get("inputs", [])
        for inp in inputs:
            ph = clean_text(inp.get("placeholder", ""))
            if ph and len(ph) >= 4 and ph not in seen_texts:
                seen_texts.add(ph)
                inp_type = inp.get("type", "text")
                candidates.append({
                    "text": ph,
                    "element_type": "input_placeholder",
                    "tag": "input",
                    "context": f"Input field (type={inp_type})"
                })

        # 4. Extract from links (call-to-actions / anchor text)
        links = scraped_data.get("links", [])
        for lnk in links:
            txt = clean_text(lnk.get("text", ""))
            # Include actionable links
            if txt and 4 <= len(txt) <= 120 and txt not in seen_texts:
                href = lnk.get("href", "")
                seen_texts.add(txt)
                candidates.append({
                    "text": txt,
                    "element_type": "link",
                    "tag": "a",
                    "context": f"Link href: {href[:80]}" if href else "Navigation link"
                })

        # 5. Extract sentences and short paragraphs from page text
        raw_text = scraped_data.get("text", "")
        if raw_text:
            lines = raw_text.splitlines()
            for line in lines:
                line_clean = clean_text(line)
                if not line_clean:
                    continue
                sentences = re.split(r"(?<=[.!?])\s+", line_clean)
                for sent in sentences:
                    sent = clean_text(sent)
                    words = sent.split()
                    if 2 <= len(words) <= 35 and len(sent) >= 6:
                        if sent not in seen_texts:
                            seen_texts.add(sent)
                            candidates.append({
                                "text": sent,
                                "element_type": "text_block",
                                "tag": "p",
                                "context": line_clean[:180] if line_clean != sent else ""
                            })

        return candidates

    def predict_candidates(self, candidates: List[Dict[str, Any]], threshold: float = 0.65) -> List[Dict[str, Any]]:
        """
        Evaluate candidate items through two-stage ML pipeline:
        Stage 1: Binary classification (Dark Pattern vs Clean)
        Stage 2: Multiclass category classification for positive detections
        
        Returns individual detection records matching Phase 6 specification.
        """
        if not self._is_loaded or not candidates:
            return []

        # Filter valid items
        valid_items = [c for c in candidates if len(c.get("text", "")) >= 4]
        if not valid_items:
            return []

        texts = [c["text"] for c in valid_items]

        # Stage 1: Binary Classification
        X_bin = self.binary_vectorizer.transform(texts)
        bin_probs = self.binary_model.predict_proba(X_bin)[:, 1]

        # Collect positive indices above threshold
        pos_indices = [i for i, p in enumerate(bin_probs) if p >= threshold]
        if not pos_indices:
            return []

        pos_items = [valid_items[i] for i in pos_indices]
        pos_texts = [texts[i] for i in pos_indices]
        pos_probs = [bin_probs[i] for i in pos_indices]

        # Stage 2: Multiclass Category Classification
        X_cat = self.category_vectorizer.transform(pos_texts)
        cat_preds = self.category_model.predict(X_cat)
        cat_probs = self.category_model.predict_proba(X_cat)
        cat_labels = self.category_encoder.inverse_transform(cat_preds)

        detections = []
        for item, prob, cat, c_prob in zip(pos_items, pos_probs, cat_labels, cat_probs):
            cat_conf = float(c_prob.max())
            meta = CATEGORY_METADATA.get(cat, {
                "severity": "Medium",
                "description": f"Potential {cat} dark pattern detected."
            })

            severity = meta["severity"]
            if prob >= 0.90 and severity == "Medium":
                severity = "High"

            detection = {
                "pattern": cat,
                "confidence": round(float(prob), 4),
                "evidence": item["text"],
                "element_type": item.get("element_type", "text_block"),
                "context": item.get("context", ""),
                "tag": item.get("tag", ""),
                "detection_method": "AI Model",
                "category_confidence": round(cat_conf, 4),
                "severity": severity,
                "description": meta["description"]
            }
            detections.append(detection)

        return detections

    def analyze_page(self, scraped_data: Dict[str, Any], threshold: float = 0.65) -> Dict[str, Any]:
        """
        Analyze a page by extracting candidates, evaluating each,
        and returning both granular detections and category summaries.
        """
        if not self._is_loaded:
            return {
                "total_dark_patterns": 0,
                "findings": [],
                "raw_detections": [],
                "engine_status": "unavailable"
            }

        candidates = self.extract_candidates(scraped_data)
        raw_detections = self.predict_candidates(candidates, threshold=threshold)

        # Group detections by pattern for aggregated findings
        grouped = {}
        for det in raw_detections:
            pat = det["pattern"]
            if pat not in grouped:
                grouped[pat] = {
                    "pattern": pat,
                    "severity": det["severity"],
                    "description": det["description"],
                    "detection_method": "AI Model",
                    "highest_confidence": det["confidence"],
                    "element_type": det["element_type"],
                    "evidence": [],
                    "evidence_items": []
                }

            if det["evidence"] not in grouped[pat]["evidence"]:
                grouped[pat]["evidence"].append(det["evidence"])
                grouped[pat]["evidence_items"].append({
                    "text": det["evidence"],
                    "element_type": det["element_type"],
                    "context": det["context"],
                    "confidence": det["confidence"]
                })

            if det["confidence"] > grouped[pat]["highest_confidence"]:
                grouped[pat]["highest_confidence"] = det["confidence"]
                grouped[pat]["severity"] = det["severity"]
                grouped[pat]["element_type"] = det["element_type"]

        findings = list(grouped.values())

        return {
            "total_dark_patterns": len(findings),
            "findings": findings,
            "raw_detections": raw_detections,
            "total_candidates_evaluated": len(candidates),
            "engine_status": "active"
        }

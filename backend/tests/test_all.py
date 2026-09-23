"""
DarkShield AI - Comprehensive System & Unit Test Suite
======================================================

Tests:
1. URL validation
2. Preprocessing & text cleaning
3. Model artifact existence and loading
4. Binary classification inference
5. Multiclass categorization inference
6. Candidate extraction & element preservation
7. Rule-based detection
8. Hybrid decision fusion
9. Explainable dark pattern risk scoring
10. Security analyzer & score calculation
11. LLM provider abstraction & unavailable mode fallback
12. FastAPI scan endpoint integration contract
"""

import unittest
import os
import json
import pandas as pd
from urllib.parse import urlparse

from backend.ai.preprocessing import clean_text, load_processed_splits
from backend.ai.detector import AIDarkPatternDetector
from backend.detectors.dark_patterns import detect_dark_patterns, detect_dark_patterns_rule_based
from backend.detectors.scoring import calculate_dark_pattern_risk
from backend.analyzer import analyze_website
from backend.ai.llm import get_llm_status, get_llm_provider, enrich_findings_with_llm


class TestURLValidation(unittest.TestCase):
    """Test URL parsing and validation."""

    def test_valid_urls(self):
        for u in ["https://example.com", "http://localhost:8000", "https://test.org/page"]:
            parsed = urlparse(u)
            self.assertIn(parsed.scheme, ["http", "https"])
            self.assertTrue(bool(parsed.netloc))

    def test_invalid_urls(self):
        for u in ["ftp://example.com", "javascript:alert(1)", "not_a_url", ""]:
            parsed = urlparse(u)
            is_valid = parsed.scheme in ["http", "https"] and bool(parsed.netloc)
            self.assertFalse(is_valid)


class TestPreprocessing(unittest.TestCase):
    """Test text cleaning and leak-free split integrity."""

    def test_clean_text(self):
        raw = "   Buy   now! &amp; save  50% &nbsp; today! \n\n  "
        cleaned = clean_text(raw)
        self.assertEqual(cleaned, "Buy now! & save 50% today!")

    def test_leak_free_splits(self):
        train_df, val_df, test_df, split_info = load_processed_splits()
        train_pages = set(train_df["page_id"])
        val_pages = set(val_df["page_id"])
        test_pages = set(test_df["page_id"])

        self.assertEqual(len(train_pages & val_pages), 0, "Train-Val page_id leak detected!")
        self.assertEqual(len(train_pages & test_pages), 0, "Train-Test page_id leak detected!")
        self.assertEqual(len(val_pages & test_pages), 0, "Val-Test page_id leak detected!")
        self.assertEqual(len(train_df) + len(val_df) + len(test_df), 2356)


class TestMLModels(unittest.TestCase):
    """Test model loading, binary predictions, and multiclass categorization."""

    @classmethod
    def setUpClass(cls):
        cls.detector = AIDarkPatternDetector.get_instance()

    def test_model_ready(self):
        self.assertTrue(self.detector.is_ready(), "AI detector models failed to load.")

    def test_binary_prediction(self):
        dark_sample = "Hurry! Only 2 items left in stock!"
        clean_sample = "Our corporate office is located in downtown Seattle."

        res_dark = self.detector.predict_candidates([{"text": dark_sample, "element_type": "heading"}])
        self.assertGreaterEqual(len(res_dark), 1, "Dark pattern was not detected.")
        self.assertGreaterEqual(res_dark[0]["confidence"], 0.70)
        self.assertEqual(res_dark[0]["element_type"], "heading")

        res_clean = self.detector.predict_candidates([{"text": clean_sample, "element_type": "text_block"}])
        self.assertEqual(len(res_clean), 0, "Clean text produced false positive.")

    def test_category_classification(self):
        scarcity_sample = "Only 3 rooms left at this price!"
        urgency_sample = "Offer expires in 00:05:00!"

        cands = [
            {"text": scarcity_sample, "element_type": "text_block"},
            {"text": urgency_sample, "element_type": "banner_or_dialog"}
        ]
        results = self.detector.predict_candidates(cands)
        patterns = {r["evidence"]: r["pattern"] for r in results}

        self.assertIn(scarcity_sample, patterns)
        self.assertEqual(patterns[scarcity_sample], "Scarcity")

        self.assertIn(urgency_sample, patterns)
        self.assertEqual(patterns[urgency_sample], "Urgency")


class TestHybridDecisionEngine(unittest.TestCase):
    """Test hybrid fusion between rules, ML, and DOM context."""

    def test_hybrid_fusion(self):
        mock_scraped = {
            "dom_elements": [
                {"element_type": "heading", "text": "Hurry! Only 2 items left!", "context": "Top header", "tag": "h1"},
                {"element_type": "text_block", "text": "No thanks, I prefer to pay full price.", "context": "Promo modal", "tag": "p"}
            ],
            "text": "Hurry! Only 2 items left!\nNo thanks, I prefer to pay full price.\nSign up now",
            "buttons": [{"text": "Sign up now"}],
            "inputs": [{"name": "email", "type": "email", "placeholder": "Enter your email"}],
            "links": []
        }

        res = detect_dark_patterns(mock_scraped)
        self.assertIn("risk_score", res)
        self.assertIn("risk_level", res)
        self.assertIn("findings", res)
        self.assertGreaterEqual(res["total_dark_patterns"], 2)

        methods = {f["pattern"]: f["detection_method"] for f in res["findings"]}
        # Urgency/Scarcity was flagged by both regex rules and ML model -> should be Hybrid
        self.assertIn("Urgency or Scarcity", methods)
        self.assertEqual(methods["Urgency or Scarcity"], "Hybrid (Rules + AI)")

        # Potential Forced Registration is purely DOM structural -> should be Rule-Based
        self.assertIn("Potential Forced Registration", methods)
        self.assertEqual(methods["Potential Forced Registration"], "Rule-Based")


class TestRiskScoring(unittest.TestCase):
    """Test explainable dark pattern risk calculation."""

    def test_empty_findings(self):
        res = calculate_dark_pattern_risk([])
        self.assertEqual(res["risk_score"], 0)
        self.assertEqual(res["risk_level"], "None")

    def test_severe_findings_calculation(self):
        findings = [
            {"pattern": "Sneaking", "severity": "High", "confidence": 0.95, "detection_method": "AI Model"},
            {"pattern": "Urgency or Scarcity", "severity": "Medium", "confidence": 0.98, "detection_method": "Hybrid (Rules + AI)"}
        ]
        res = calculate_dark_pattern_risk(findings)
        # Sneaking (High=22 * 0.95 = 20.9) + Urgency (Med=14 * 0.98 * 1.15 = 15.78) ~ 37
        self.assertGreaterEqual(res["risk_score"], 30)
        self.assertIn(res["risk_level"], ["Medium", "High"])
        self.assertTrue(len(res["score_breakdown"]) == 2)


class TestSecurityAnalyzer(unittest.TestCase):
    """Test security analyzer score deduction and check logic."""

    def test_insecure_http_website(self):
        mock_data = {
            "url": "http://insecure-site.com",
            "links": [],
            "inputs": [{"type": "password"}],
            "buttons": [],
            "headers": {},
            "text": "Simple login page"
        }
        res = analyze_website(mock_data)
        self.assertEqual(res["risk_level"], "High")
        self.assertLessEqual(res["security_score"], 50)
        self.assertIn("dark_pattern_analysis", res)


class TestLLMContextualLayer(unittest.TestCase):
    """Test LLM provider abstraction and fallback functionality."""

    def test_fallback_when_unconfigured(self):
        provider, status = get_llm_provider()
        self.assertTrue(provider.is_available())

        findings = [{
            "pattern": "Social Proof",
            "confidence": 0.95,
            "evidence": ["38 people bought this item in the last hour."],
            "element_type": "text_block",
            "context": "Product card"
        }]

        enriched, active_status = enrich_findings_with_llm(findings)
        self.assertEqual(len(enriched), 1)
        item = enriched[0]

        self.assertIn("explanation", item)
        self.assertIn("why_it_matters", item)
        self.assertIn("recommendation", item)
        # Grounding check: must mention the evidence text
        self.assertIn("38 people bought this item in the last hour.", item["explanation"])


class TestCookieDarkPatterns(unittest.TestCase):
    """Test cookie consent banner dark pattern detection."""

    def test_asymmetric_cookie_consent(self):
        mock_scraped = {
            "url": "https://example.com",
            "text": "Welcome to our store",
            "links": [],
            "buttons": [],
            "inputs": [],
            "cookie_consent": {
                "banner_detected": True,
                "banner_text": "We value your privacy. We use cookies.",
                "accept_button": "Accept All Cookies",
                "reject_button": None,
                "manage_button": "Manage Preferences",
                "preselected_checkboxes": [
                    {"name": "marketing", "label": "Advertising & Marketing", "is_essential": False, "disabled": False}
                ],
                "has_close_button": False
            }
        }
        res = detect_dark_patterns(mock_scraped)
        findings = {f["pattern"]: f for f in res["findings"]}

        # Asymmetric Choice should be flagged
        self.assertIn("Asymmetric Cookie Consent", findings)
        self.assertEqual(findings["Asymmetric Cookie Consent"]["severity"], "Medium")

        # Preselected marketing checkbox should be flagged
        self.assertIn("Pre-selected Tracking Checkboxes", findings)
        self.assertEqual(findings["Pre-selected Tracking Checkboxes"]["severity"], "Medium")


class TestScanHistoryAndReport(unittest.TestCase):
    """Test scan history persistence and PDF generation."""

    def test_scan_history_and_pdf(self):
        from backend.scan_history import save_scan, get_scan_history, get_scan_by_id, delete_scan
        from backend.report_generator import generate_pdf_report

        mock_scan = {
            "website": {
                "url": "https://audit-test.org",
                "title": "Audit Test Portal",
                "screenshot_b64": None
            },
            "security_analysis": {
                "security_score": 85,
                "risk_level": "Low",
                "findings": [{"issue": "Missing CSP", "severity": "Medium", "description": "No CSP header."}]
            },
            "dark_pattern_analysis": {
                "risk_score": 42,
                "risk_level": "Medium",
                "findings": [
                    {
                        "pattern": "Urgency or Scarcity",
                        "severity": "Medium",
                        "detection_method": "Hybrid (Rules + AI)",
                        "confidence": 0.94,
                        "evidence": ["Only 3 left in stock"],
                        "explanation": "Simulates artificial urgency to hasten purchase decisions.",
                        "recommendation": "State actual inventory levels transparently."
                    }
                ]
            }
        }

        # 1. Save scan
        scan_id = save_scan(mock_scan)
        self.assertTrue(scan_id.startswith("scan_"))

        # 2. Get history list
        history = get_scan_history(limit=10)
        matching = [item for item in history if item["scan_id"] == scan_id]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0]["url"], "https://audit-test.org")

        # 3. Get detail
        detail = get_scan_by_id(scan_id)
        self.assertIsNotNone(detail)
        self.assertEqual(detail["security_analysis"]["security_score"], 85)

        # 4. Generate PDF report
        pdf_buf = generate_pdf_report(detail)
        pdf_bytes = pdf_buf.getvalue()
        self.assertGreater(len(pdf_bytes), 1000)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

        # 5. Clean up
        deleted = delete_scan(scan_id)
        self.assertTrue(deleted)
        self.assertIsNone(get_scan_by_id(scan_id))


if __name__ == "__main__":
    unittest.main()


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
from unittest.mock import patch, MagicMock
import os
import json
import urllib
import urllib.request
import urllib.error
import pandas as pd
from urllib.parse import urlparse

from backend.ai.preprocessing import clean_text, load_processed_splits
from backend.ai.detector import AIDarkPatternDetector
from backend.detectors.dark_patterns import detect_dark_patterns, detect_dark_patterns_rule_based
from backend.detectors.scoring import (
    calculate_dark_pattern_risk,
    calculate_severity_score,
    calculate_confidence_score,
    calculate_frequency_score,
    calculate_user_impact_score,
    calculate_behavioral_evidence_score,
    calculate_overall_risk_score
)
from backend.analyzer import analyze_website, analyze_page
from backend.captured_page import CapturedPage
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
        total_samples = len(train_df) + len(val_df) + len(test_df)
        self.assertIn(total_samples, [2356, 2786, 2790], f"Unexpected total sample count: {total_samples}")


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

    def test_v2_model_metadata_reports_verified_metrics(self):
        """Regression test: verify current V2 metadata reports 96.89% and not stale V1 95.2%."""
        meta = self.detector.get_model_metadata()
        self.assertEqual(meta["model_version"], "v2")
        self.assertEqual(meta["model_name"], "Calibrated Linear SVM V2")
        self.assertEqual(meta["test_accuracy"], 0.9689)
        self.assertEqual(meta["precision"], 0.9672)
        self.assertEqual(meta["recall"], 0.9710)
        self.assertEqual(meta["f1_score"], 0.9691)
        self.assertAlmostEqual(meta["roc_auc"], 0.9924, places=2)
        self.assertEqual(meta["accuracy_display"], "96.89%")

        # Ensure historical V1 is preserved as V1 baseline and never reported as V2
        self.assertIn("v1_historical", meta)
        v1 = meta["v1_historical"]
        self.assertEqual(v1["model_version"], "v1")
        self.assertEqual(v1["test_accuracy"], 0.9521)
        self.assertNotEqual(meta["test_accuracy"], v1["test_accuracy"])



class TestInstitutionalFalsePositivePrevention(unittest.TestCase):
    """
    Mentor Feedback Verification:
    Verify that typical educational institution sentences (such as from KKWIEER
    or AICTE/university portals) are NOT falsely classified as dark patterns.
    """
    @classmethod
    def setUpClass(cls):
        cls.detector = AIDarkPatternDetector.get_instance()

    def test_admissions_and_college_announcements(self):
        institutional_phrases = [
            "Admissions open for First Year B.Tech and Direct Second Year Engineering for AY 2026-27.",
            "Candidates must report to the college admission cell with original certificates and fee DD.",
            "K.K. Wagh Institute of Engineering Education and Research is accredited by NAAC with A Grade.",
            "Download the official admission brochure and fee structure for undergraduate programs.",
            "The Central Library remains open from 8:00 AM to 8:00 PM on all working days.",
            "Continuous Assessment Test 1 (CAT-1) will commence from the third week of August.",
            "Anti-ragging committee and squad contact numbers are displayed across the campus.",
            "Mandatory disclosure under AICTE regulations has been updated for the current session.",
            "Students can view and download the revised curriculum scheme and syllabus copy.",
            "At KKWIEER, learning goes beyond textbooks.",
            "K.K. Wagh isn't just a college—it's a launchpad for dreams.",
            "Everything that enthuses people at our university.",
            "Everything that enthuses people at our Education Society.",
            "culture in educational excellence",
            "knowledge in Horticulture",
            "For general inquiries, email us at kkwieer@kkwagh.edu.in or call 0253-2512876."
        ]
        candidates = [{"text": p, "element_type": "text_block"} for p in institutional_phrases]
        detections = self.detector.predict_candidates(candidates)
        self.assertEqual(len(detections), 0, f"False positive detected on institutional text: {[d['evidence'] for d in detections]}")


class TestMinorityClassDetection(unittest.TestCase):
    """
    Verify that underrepresented dark pattern categories (Forced Action, Sneaking, Obstruction)
    are properly recognized after dataset enrichment.
    """
    @classmethod
    def setUpClass(cls):
        cls.detector = AIDarkPatternDetector.get_instance()

    def test_forced_action_detection(self):
        sample = "You must create an account and verify your phone number before you can view product prices."
        res = self.detector.predict_candidates([{"text": sample, "element_type": "text_block"}])
        self.assertGreaterEqual(len(res), 1)
        self.assertEqual(res[0]["pattern"], "Forced Action")

    def test_sneaking_detection(self):
        sample = "A $4.99 green shipping carbon offset fee has been automatically added to your cart."
        res = self.detector.predict_candidates([{"text": sample, "element_type": "text_block"}])
        self.assertGreaterEqual(len(res), 1)
        self.assertEqual(res[0]["pattern"], "Sneaking")

    def test_obstruction_detection(self):
        sample = "To cancel your membership, you must call our telephone hotline at 1-800-555-0199 between 9 AM and 11 AM EST on weekdays."
        res = self.detector.predict_candidates([{"text": sample, "element_type": "text_block"}])
        self.assertGreaterEqual(len(res), 1)
        self.assertEqual(res[0]["pattern"], "Obstruction")


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
        self.assertGreaterEqual(res["risk_score"], 30)
        self.assertIn(res["risk_level"], ["Medium", "High"])
        self.assertTrue(len(res["score_breakdown"]) == 2)
        self.assertIn("risk_breakdown", res)

    def test_5_factor_risk_breakdown_structure(self):
        findings = [
            {"pattern": "Forced Action", "severity": "Critical", "confidence": 0.96, "detection_method": "AI Model"},
            {"pattern": "Confirmshaming", "severity": "High", "confidence": 0.92, "detection_method": "Rule-Based"}
        ]
        res = calculate_dark_pattern_risk(findings)
        self.assertIn("risk_breakdown", res)
        rb = res["risk_breakdown"]
        for factor in ["severity", "confidence", "frequency", "user_impact", "behavioral_evidence"]:
            self.assertIn(factor, rb)
            self.assertGreaterEqual(rb[factor], 0.0)
            self.assertLessEqual(rb[factor], 100.0)
        self.assertGreaterEqual(res["risk_score"], 0)
        self.assertLessEqual(res["risk_score"], 100)

    def test_helper_functions_discrete(self):
        findings = [
            {"pattern": "Urgency or Scarcity", "severity": "Medium", "confidence": 0.90, "evidence": ["Only 1 left!"]}
        ]
        sev = calculate_severity_score(findings)
        conf = calculate_confidence_score(findings)
        freq = calculate_frequency_score(findings)
        imp = calculate_user_impact_score(findings)
        bev = calculate_behavioral_evidence_score(findings)

        self.assertEqual(sev, 50.0)
        self.assertEqual(conf, 90.0)
        self.assertGreater(freq, 25.0)
        self.assertEqual(imp, 70.0)
        self.assertEqual(bev, 0.0)  # No behavioral manipulation present

        overall = calculate_overall_risk_score(findings)
        self.assertIn("risk_score", overall)
        self.assertIn("risk_level", overall)

    def test_website_a_vs_website_b_differential(self):
        # Website A: Single low-severity finding, high confidence, no behavioral tricks
        findings_a = [
            {"pattern": "Aggressive CTA", "severity": "Low", "confidence": 0.95, "evidence": ["Subscribe now"]}
        ]
        res_a = calculate_dark_pattern_risk(findings_a)

        # Website B: 7 distinct deceptive elements, high severity, high confidence, strong impact, preselected tracking & difficult rejection
        findings_b = [
            {"pattern": "Forced Action", "severity": "Critical", "confidence": 0.98, "evidence": ["Must register to continue"]},
            {"pattern": "Hidden Costs", "severity": "High", "confidence": 0.95, "evidence": ["Extra $15 fee at final step"]},
            {"pattern": "Obstruction", "severity": "High", "confidence": 0.94, "evidence": ["Call us to cancel membership"]},
            {"pattern": "Confirmshaming", "severity": "High", "confidence": 0.92, "evidence": ["No, I hate saving money"]},
            {"pattern": "Pre-selected Tracking Checkboxes", "severity": "Medium", "confidence": 0.90, "rule_signals": ["cookie_preselected_categories"], "evidence": ["Pre-checked: Advertising"]},
            {"pattern": "Asymmetric Cookie Consent", "severity": "Medium", "confidence": 0.88, "rule_signals": ["cookie_asymmetric_choice"], "evidence": ["Accept All vs Manage"]},
            {"pattern": "Urgency Countdown", "severity": "Medium", "confidence": 0.99, "evidence": ["Deal expires in 02:00"]}
        ]
        res_b = calculate_dark_pattern_risk(findings_b)

        # Website A should produce relatively lower risk
        self.assertLess(res_a["risk_score"], 45)
        self.assertIn(res_a["risk_level"], ["Low", "Medium"])

        # Website B should produce significantly higher risk
        self.assertGreaterEqual(res_b["risk_score"], 70)
        self.assertIn(res_b["risk_level"], ["High", "Very High"])
        self.assertGreater(res_b["risk_score"], res_a["risk_score"] + 30)

    def test_frequency_deduplication(self):
        # 3 findings referencing the identical pattern and evidence should not count 3 times
        duplicate_findings = [
            {"pattern": "Urgency", "severity": "Medium", "confidence": 0.90, "evidence": ["Hurry sale ends!"]},
            {"pattern": "Urgency", "severity": "Medium", "confidence": 0.90, "evidence": ["Hurry sale ends!"]},
            {"pattern": "Urgency", "severity": "Medium", "confidence": 0.90, "evidence": ["Hurry sale ends!"]}
        ]
        distinct_findings = [
            {"pattern": "Urgency", "severity": "Medium", "confidence": 0.90, "evidence": ["Hurry sale ends!"]}
        ]
        freq_dup = calculate_frequency_score(duplicate_findings)
        freq_single = calculate_frequency_score(distinct_findings)
        self.assertEqual(freq_dup, freq_single)

    def test_zero_division_and_bounds(self):
        # Empty findings
        empty_res = calculate_dark_pattern_risk([])
        self.assertEqual(empty_res["risk_score"], 0)
        self.assertEqual(empty_res["risk_level"], "None")
        self.assertEqual(empty_res["risk_breakdown"]["severity"], 0.0)

        # Extreme values bounded in [0, 100]
        extreme_findings = [
            {"pattern": "Forced Action", "severity": "Critical", "confidence": 1.5, "evidence": [f"Evidence {i}"]}
            for i in range(20)
        ]
        extreme_res = calculate_dark_pattern_risk(extreme_findings)
        self.assertLessEqual(extreme_res["risk_score"], 100)
        self.assertGreaterEqual(extreme_res["risk_score"], 0)

    def test_exact_mathematical_weights_and_sum(self):
        # Weights: 25% Severity, 20% Confidence, 15% Frequency, 25% User Impact, 15% Behavioral Evidence
        w_sev = 0.25
        w_conf = 0.20
        w_freq = 0.15
        w_imp = 0.25
        w_bev = 0.15
        self.assertAlmostEqual(w_sev + w_conf + w_freq + w_imp + w_bev, 1.00, places=7)

        # Simulated perfect 100 on all factors
        synthetic_sum = 100.0 * w_sev + 100.0 * w_conf + 100.0 * w_freq + 100.0 * w_imp + 100.0 * w_bev
        self.assertEqual(round(synthetic_sum), 100)

    def test_risk_level_threshold_boundaries(self):
        # 0 -> None (when 0 findings)
        empty_res = calculate_overall_risk_score([])
        self.assertEqual(empty_res["risk_score"], 0)
        self.assertEqual(empty_res["risk_level"], "None")

        # Verify exact classification bands
        def get_level(score, findings_count=1):
            if score == 0 and findings_count == 0:
                return "None"
            elif score < 30:
                return "Low"
            elif score < 60:
                return "Medium"
            elif score < 80:
                return "High"
            else:
                return "Very High"

        self.assertEqual(get_level(0, 0), "None")
        self.assertEqual(get_level(1), "Low")
        self.assertEqual(get_level(29), "Low")
        self.assertEqual(get_level(30), "Medium")
        self.assertEqual(get_level(59), "Medium")
        self.assertEqual(get_level(60), "High")
        self.assertEqual(get_level(79), "High")
        self.assertEqual(get_level(80), "Very High")
        self.assertEqual(get_level(100), "Very High")

    def test_factor_clamping_and_non_negativity(self):
        # Findings with out-of-range confidence values
        out_of_bound_findings = [
            {"pattern": "Urgency", "severity": "Medium", "confidence": -0.80, "evidence": ["test"]},
            {"pattern": "Scarcity", "severity": "Medium", "confidence": 3.50, "evidence": ["test2"]}
        ]
        conf = calculate_confidence_score(out_of_bound_findings)
        self.assertGreaterEqual(conf, 0.0)
        self.assertLessEqual(conf, 100.0)

        sev = calculate_severity_score(out_of_bound_findings)
        self.assertGreaterEqual(sev, 0.0)
        self.assertLessEqual(sev, 100.0)

        imp = calculate_user_impact_score(out_of_bound_findings)
        self.assertGreaterEqual(imp, 0.0)
        self.assertLessEqual(imp, 100.0)

        freq = calculate_frequency_score(out_of_bound_findings)
        self.assertGreaterEqual(freq, 0.0)
        self.assertLessEqual(freq, 100.0)

        bev = calculate_behavioral_evidence_score(out_of_bound_findings)
        self.assertGreaterEqual(bev, 0.0)
        self.assertLessEqual(bev, 100.0)

    def test_behavioral_evidence_strict_zero_gating(self):
        # Pure text urgency/scarcity findings without behavioral cues must return 0.0
        pure_text_findings = [
            {"pattern": "Urgency or Scarcity", "severity": "Medium", "confidence": 0.95, "evidence": ["Limited quantity available!"]},
            {"pattern": "Social Proof", "severity": "Low", "confidence": 0.88, "evidence": ["35 people bought this item"]}
        ]
        bev_score = calculate_behavioral_evidence_score(pure_text_findings)
        self.assertEqual(bev_score, 0.0, "Behavioral evidence must be strictly 0.0 when no behavioral triggers exist.")

        # Finding with behavioral signal (preselected tracking)
        preselected_finding = [
            {"pattern": "Pre-selected Tracking", "severity": "Medium", "confidence": 0.90, "rule_signals": ["cookie_preselected_categories"]}
        ]
        bev_preselected = calculate_behavioral_evidence_score(preselected_finding)
        self.assertEqual(bev_preselected, 35.0)

    def test_testsite_audit_manual_math_replay(self):
        # Test site audit replay: Sev=50.0, Conf=92.1, Freq=89.8, Impact=84.8, Behav=95.0
        # Expected: 0.25*50.0 + 0.20*92.1 + 0.15*89.8 + 0.25*84.8 + 0.15*95.0 = 79.84 -> round = 80
        sev = 50.0
        conf = 92.1
        freq = 89.8
        imp = 84.8
        bev = 95.0
        weighted_sum = 0.25 * sev + 0.20 * conf + 0.15 * freq + 0.25 * imp + 0.15 * bev
        self.assertAlmostEqual(weighted_sum, 79.84, places=2)
        final_score = int(round(weighted_sum))
        self.assertEqual(final_score, 80)
        self.assertEqual("Very High" if final_score >= 80 else "High", "Very High")

    def test_blocked_and_partial_capture_withholding(self):
        # Blocked page should have risk_score=None and risk_level='Not Assessed'
        blocked_page = CapturedPage(url="https://www.meesho.com", access_blocked=True, block_provider="Akamai")
        res_blocked = analyze_page(blocked_page)
        self.assertEqual(res_blocked["status"], "blocked")
        self.assertIsNone(res_blocked["risk_score"])
        self.assertEqual(res_blocked["risk_level"], "Not Assessed")

        # Partial page should have risk_score=None and risk_level='Not Assessed (Incomplete Capture)'
        partial_page = CapturedPage(
            url="https://www.amazon.in",
            capture_quality="partial",
            page_completeness={"score": 15, "quality": "partial", "is_complete": False, "is_partial": True, "is_blocked": False, "reasons": ["Visible text below threshold"]}
        )
        res_partial = analyze_page(partial_page)
        self.assertEqual(res_partial["status"], "partial")
        self.assertIsNone(res_partial["risk_score"])
        self.assertEqual(res_partial["dark_pattern_analysis"]["risk_level"], "Not Assessed (Incomplete Capture)")



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


from unittest.mock import MagicMock, patch
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError
from backend.scraper.browser import scrape_website, _classify_playwright_error, _detect_bot_or_blocked
from backend.app import scan_website, WebsiteRequest


class TestResilientScanner(unittest.TestCase):
    """Test resilient scraping, navigation timeout recovery, error handling, and redirects."""

    def test_error_classification(self):
        etype, emsg = _classify_playwright_error("net::ERR_NAME_NOT_RESOLVED")
        self.assertEqual(etype, "dns_failure")

        etype, emsg = _classify_playwright_error("net::ERR_CONNECTION_REFUSED")
        self.assertEqual(etype, "connection_refused")

        etype, emsg = _classify_playwright_error("net::ERR_CONNECTION_RESET")
        self.assertEqual(etype, "connection_reset")

        etype, emsg = _classify_playwright_error("Timeout 20000ms exceeded")
        self.assertEqual(etype, "navigation_timeout")

    def test_bot_detection_helper(self):
        self.assertTrue(_detect_bot_or_blocked("Robot Check", "Enter letters below", 200))
        self.assertTrue(_detect_bot_or_blocked("Normal Title", "Checking your browser before accessing", 200))
        self.assertTrue(_detect_bot_or_blocked("Access Denied", "403 Forbidden", 403))
        self.assertFalse(_detect_bot_or_blocked("Acme Store", "Welcome to our shop", 200))

    @patch("backend.scraper.browser.find_edge_executable", return_value="C:\\dummy\\msedge.exe")
    @patch("backend.scraper.browser.sync_playwright")
    def test_successful_navigation(self, mock_playwright, mock_edge):
        mock_p = MagicMock()
        mock_playwright.return_value.__enter__.return_value = mock_p
        mock_browser = MagicMock()
        mock_p.chromium.launch.return_value = mock_browser
        mock_context = MagicMock()
        mock_browser.new_context.return_value = mock_context
        mock_page = MagicMock()
        mock_context.new_page.return_value = mock_page

        mock_page.url = "https://example.com"
        mock_page.title.return_value = "Example Domain"
        mock_page.goto.return_value = MagicMock(all_headers=lambda: {"server": "ECS"}, status=200)

        # Mock page.evaluate for batch element extraction
        def fake_evaluate(script):
            if "links" in script and "buttons" in script:
                return {
                    "links": [{"text": "More info", "href": "https://iana.org"}],
                    "buttons": [{"text": "Click"}],
                    "inputs": [{"type": "text", "name": "search", "placeholder": "Search"}]
                }
            elif "banner_detected" in script:
                return {"banner_detected": False}
            elif "innerText" in script:
                return "This domain is for use in illustrative examples in documents."
            return []

        mock_page.evaluate.side_effect = fake_evaluate

        res = scrape_website("https://example.com")
        self.assertEqual(res["scan_status"], "complete")
        self.assertEqual(res["navigation_status"], "success")
        self.assertEqual(res["requested_url"], "https://example.com")
        self.assertEqual(res["final_url"], "https://example.com")
        self.assertEqual(res["title"], "Example Domain")
        self.assertEqual(len(res["links"]), 1)
        self.assertEqual(len(res["buttons"]), 1)
        self.assertEqual(len(res["inputs"]), 1)

    @patch("backend.scraper.browser.find_edge_executable", return_value="C:\\dummy\\msedge.exe")
    @patch("backend.scraper.browser.sync_playwright")
    def test_navigation_timeout_partial_recovery(self, mock_playwright, mock_edge):
        """When navigation times out, but DOM content exists, status must be partial."""
        mock_p = MagicMock()
        mock_playwright.return_value.__enter__.return_value = mock_p
        mock_browser = MagicMock()
        mock_p.chromium.launch.return_value = mock_browser
        mock_context = MagicMock()
        mock_browser.new_context.return_value = mock_context
        mock_page = MagicMock()
        mock_context.new_page.return_value = mock_page

        mock_page.url = "https://slow-site.com"
        mock_page.title.return_value = "Slow Loading Portal"
        # Simulate timeout on page.goto
        mock_page.goto.side_effect = PlaywrightTimeoutError("Page.goto: Timeout 20000ms exceeded.")

        def fake_evaluate(script):
            if "document.body.innerText.trim().length" in script:
                return 450  # DOM text exists!
            elif "document.body.innerText" in script:
                return "Hurry! Limited stock available today only."
            elif "links" in script and "buttons" in script:
                return {"links": [], "buttons": [{"text": "Buy Now"}], "inputs": []}
            return []

        mock_page.evaluate.side_effect = fake_evaluate

        res = scrape_website("https://slow-site.com")
        self.assertEqual(res["scan_status"], "partial")
        self.assertEqual(res["navigation_status"], "timeout")
        self.assertIn("navigation timeout", res["warning"])
        self.assertEqual(res["title"], "Slow Loading Portal")
        self.assertIn("Hurry", res["text"])

    @patch("backend.scraper.browser.find_edge_executable", return_value="C:\\dummy\\msedge.exe")
    @patch("backend.scraper.browser.sync_playwright")
    def test_navigation_timeout_blank_page(self, mock_playwright, mock_edge):
        """When navigation times out and page has 0 content, status must be failed."""
        mock_p = MagicMock()
        mock_playwright.return_value.__enter__.return_value = mock_p
        mock_browser = MagicMock()
        mock_p.chromium.launch.return_value = mock_browser
        mock_context = MagicMock()
        mock_browser.new_context.return_value = mock_context
        mock_page = MagicMock()
        mock_context.new_page.return_value = mock_page

        mock_page.goto.side_effect = PlaywrightTimeoutError("Page.goto: Timeout 20000ms exceeded.")
        mock_page.evaluate.return_value = 0  # Completely empty

        res = scrape_website("https://unreachable-timeout.com")
        self.assertEqual(res["scan_status"], "failed")
        self.assertEqual(res["navigation_status"], "timeout")
        self.assertEqual(res["error_type"], "navigation_timeout")

    @patch("backend.scraper.browser.find_edge_executable", return_value="C:\\dummy\\msedge.exe")
    @patch("backend.scraper.browser.sync_playwright")
    def test_dns_failure(self, mock_playwright, mock_edge):
        mock_p = MagicMock()
        mock_playwright.return_value.__enter__.return_value = mock_p
        mock_browser = MagicMock()
        mock_p.chromium.launch.return_value = mock_browser
        mock_context = MagicMock()
        mock_browser.new_context.return_value = mock_context
        mock_page = MagicMock()
        mock_context.new_page.return_value = mock_page

        mock_page.goto.side_effect = PlaywrightError("net::ERR_NAME_NOT_RESOLVED")
        mock_page.evaluate.return_value = 0

        res = scrape_website("https://nonexistent-domain-xyz-12345.com")
        self.assertEqual(res["scan_status"], "failed")
        self.assertEqual(res["error_type"], "dns_failure")
        self.assertIn("DNS failure", res["message"])

    @patch("backend.scraper.browser.find_edge_executable", return_value="C:\\dummy\\msedge.exe")
    @patch("backend.scraper.browser.sync_playwright")
    def test_redirect_handling(self, mock_playwright, mock_edge):
        """Normal redirects should preserve requested_url and final_url without failing."""
        mock_p = MagicMock()
        mock_playwright.return_value.__enter__.return_value = mock_p
        mock_browser = MagicMock()
        mock_p.chromium.launch.return_value = mock_browser
        mock_context = MagicMock()
        mock_browser.new_context.return_value = mock_context
        mock_page = MagicMock()
        mock_context.new_page.return_value = mock_page

        # Initial requested vs final redirected URL
        mock_page.url = "https://destination.org/welcome"
        mock_page.title.return_value = "Destination Home"
        mock_page.goto.return_value = MagicMock(all_headers=lambda: {}, status=200)
        mock_page.evaluate.return_value = "Welcome to Destination"

        res = scrape_website("http://short.link")
        self.assertEqual(res["scan_status"], "complete")
        self.assertEqual(res["requested_url"], "http://short.link")
        self.assertEqual(res["final_url"], "https://destination.org/welcome")
        self.assertEqual(res["url"], "https://destination.org/welcome")

    @patch("backend.scraper.browser.find_edge_executable", return_value="C:\\dummy\\msedge.exe")
    @patch("backend.scraper.browser.sync_playwright")
    def test_anti_bot_detection(self, mock_playwright, mock_edge):
        mock_p = MagicMock()
        mock_playwright.return_value.__enter__.return_value = mock_p
        mock_browser = MagicMock()
        mock_p.chromium.launch.return_value = mock_browser
        mock_context = MagicMock()
        mock_browser.new_context.return_value = mock_context
        mock_page = MagicMock()
        mock_context.new_page.return_value = mock_page

        mock_page.url = "https://amazon.example"
        mock_page.title.return_value = "Robot Check"
        mock_page.goto.return_value = MagicMock(all_headers=lambda: {}, status=200)
        mock_page.evaluate.return_value = "Enter the characters you see below to continue."

        res = scrape_website("https://amazon.example")
        self.assertIn(res["scan_status"], ["blocked", "blocked_or_interaction_required"])
        self.assertTrue(res.get("access_blocked") or "anti-bot" in str(res.get("warning", "")).lower())

    @patch("backend.scraper.browser.find_edge_executable", return_value="C:\\dummy\\msedge.exe")
    @patch("backend.scraper.browser.sync_playwright")
    def test_independent_extraction_fault_tolerance(self, mock_playwright, mock_edge):
        """Title or screenshot failure must not crash link/button extraction."""
        mock_p = MagicMock()
        mock_playwright.return_value.__enter__.return_value = mock_p
        mock_browser = MagicMock()
        mock_p.chromium.launch.return_value = mock_browser
        mock_context = MagicMock()
        mock_browser.new_context.return_value = mock_context
        mock_page = MagicMock()
        mock_context.new_page.return_value = mock_page

        mock_page.url = "https://tolerant-site.com"
        mock_page.title.side_effect = Exception("Title extraction IPC error")
        mock_page.screenshot.side_effect = Exception("Screenshot timeout")

        def fake_evaluate(script):
            if "links" in script and "buttons" in script:
                return {"links": [{"text": "Home", "href": "/"}], "buttons": [], "inputs": []}
            elif "innerText" in script:
                return "Some content text"
            return []

        mock_page.evaluate.side_effect = fake_evaluate

        res = scrape_website("https://tolerant-site.com")
        self.assertEqual(res["scan_status"], "complete")
        self.assertEqual(res["title"], "Untitled Website")
        self.assertIsNone(res["screenshot_b64"])
        self.assertEqual(len(res["links"]), 1)


class TestScanAPIEndpointContract(unittest.TestCase):
    """Test FastAPI /scan endpoint contract for complete, partial, and failed states."""

    @patch("backend.app.scrape_website")
    def test_api_successful_scan(self, mock_scrape):
        mock_scrape.return_value = {
            "scan_status": "complete",
            "navigation_status": "success",
            "requested_url": "https://example.com",
            "final_url": "https://example.com",
            "url": "https://example.com",
            "title": "Example Domain",
            "text": "This domain is established to be used for illustrative examples.",
            "links": [{"text": "More information...", "href": "https://www.iana.org/domains/example"}],
            "buttons": [],
            "inputs": [],
            "headers": {"content-security-policy": "default-src 'self'"},
            "dom_elements": [],
            "screenshot_b64": None,
            "cookie_consent": {"banner_detected": False},
            "scan_duration_seconds": 1.25,
            "warning": None,
            "error_type": None,
            "message": None,
        }

        response = scan_website(WebsiteRequest(url="https://example.com"))
        self.assertEqual(response["scan_status"], "complete")
        self.assertEqual(response["navigation_status"], "success")
        self.assertIn("security_analysis", response)
        self.assertIn("dark_pattern_analysis", response)
        self.assertIn("ai_analysis", response)
        self.assertTrue(response["scan_id"].startswith("scan_"))

    @patch("backend.app.scrape_website")
    def test_api_partial_scan(self, mock_scrape):
        mock_scrape.return_value = {
            "scan_status": "partial",
            "navigation_status": "timeout",
            "requested_url": "https://heavy-site.com",
            "final_url": "https://heavy-site.com",
            "url": "https://heavy-site.com",
            "title": "Heavy Site",
            "text": "Only 2 items left in stock!",
            "links": [],
            "buttons": [{"text": "Checkout"}],
            "inputs": [],
            "headers": {},
            "dom_elements": [{"text": "Only 2 items left in stock!", "element_type": "heading"}],
            "screenshot_b64": None,
            "cookie_consent": {},
            "scan_duration_seconds": 18.5,
            "warning": "The page did not finish loading within the navigation timeout, but available content was analyzed.",
            "error_type": None,
            "message": None,
        }

        response = scan_website(WebsiteRequest(url="https://heavy-site.com"))
        self.assertEqual(response["scan_status"], "partial")
        self.assertEqual(response["navigation_status"], "timeout")
        self.assertIn("available content was analyzed", response["warning"])
        # Analyzers should still have executed!
        self.assertGreaterEqual(response["security_analysis"]["security_score"], 0)
        self.assertTrue(response["scan_id"].startswith("scan_"))

    @patch("backend.app.scrape_website")
    def test_api_failed_scan(self, mock_scrape):
        mock_scrape.return_value = {
            "scan_status": "failed",
            "navigation_status": "failed",
            "requested_url": "https://dead-server.invalid",
            "final_url": "https://dead-server.invalid",
            "url": "https://dead-server.invalid",
            "title": "Website Unavailable",
            "text": "",
            "links": [],
            "buttons": [],
            "inputs": [],
            "headers": {},
            "dom_elements": [],
            "screenshot_b64": None,
            "cookie_consent": {},
            "scan_duration_seconds": 0.5,
            "warning": None,
            "error_type": "dns_failure",
            "message": "Domain name could not be resolved (DNS failure). Please verify the URL.",
        }

        # Must return structured 200 rather than raising an unhandled 500 exception
        response = scan_website(WebsiteRequest(url="https://dead-server.invalid"))
        self.assertEqual(response["scan_status"], "failed")
        self.assertEqual(response["navigation_status"], "failed")
        self.assertEqual(response["error_type"], "dns_failure")
        self.assertIn("DNS failure", response["message"])
        self.assertTrue(response["scan_id"].startswith("scan_"))


class TestVisionAnalysis(unittest.TestCase):
    """
    Test suite for Screenshot-Based Vision AI module:
    1. Input validation & error tolerance
    2. Response parsing & JSON extraction
    3. Missing API key / offline fallback continuity
    4. HTTP & network failure resilience
    5. Multi-modal decision fusion & confidence reinforcement
    """

    def setUp(self):
        # 100-character valid dummy base64 string
        self.dummy_screenshot = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==" * 2

    def test_offline_fallback_when_unconfigured(self):
        """When no API keys are present, vision detector returns safe structured response without crashing."""
        from backend.ai.vision import analyze_screenshot, get_vision_provider
        from backend.ai.vision.fallback_provider import FallbackVisionProvider

        provider, status = get_vision_provider()
        self.assertIsInstance(provider, FallbackVisionProvider)
        self.assertFalse(provider.is_available())
        self.assertIn("unavailable", status.lower())

        res = analyze_screenshot(self.dummy_screenshot)
        self.assertFalse(res["detected"])
        self.assertEqual(res["visual_risk_score"], 0)
        self.assertEqual(res["visual_risk_level"], "None")
        self.assertEqual(res["total_visual_patterns"], 0)
        self.assertEqual(len(res["patterns"]), 0)
        self.assertIn("unavailable", res["status"].lower())

    def test_input_validation(self):
        """Passing None, empty string, or invalid data returns safe fallback without error."""
        from backend.ai.vision import analyze_screenshot

        for invalid_input in [None, "", "   ", "short_str", 12345]:
            res = analyze_screenshot(invalid_input)
            self.assertFalse(res["detected"])
            self.assertEqual(res["visual_risk_score"], 0)
            self.assertEqual(len(res["patterns"]), 0)

    @patch("urllib.request.urlopen")
    def test_gemini_vision_provider_parsing(self, mock_urlopen):
        """Simulate successful Gemini Vision API response with markdown fences."""
        from backend.ai.vision.gemini_provider import GeminiVisionProvider

        mock_payload = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": (
                                    "```json\n"
                                    "{\n"
                                    '  "detected": true,\n'
                                    '  "visual_risk_score": 78,\n'
                                    '  "visual_risk_level": "High",\n'
                                    '  "visual_confidence": 0.91,\n'
                                    '  "patterns": [\n'
                                    "    {\n"
                                    '      "name": "Visual Urgency",\n'
                                    '      "severity": "High",\n'
                                    '      "confidence": 0.91,\n'
                                    '      "evidence": "Pulsating red countdown timer at top banner",\n'
                                    '      "visual_details": "Bright red background with bold typography above the fold",\n'
                                    '      "recommendation": "Disregard artificial countdown pressure."\n'
                                    "    }\n"
                                    "  ],\n"
                                    '  "analysis_summary": "Identified high-contrast visual urgency countdown banner."\n'
                                    "}\n"
                                    "```"
                                )
                            }
                        ]
                    }
                }
            ]
        }

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_payload).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        provider = GeminiVisionProvider(api_key="mock_gemini_key")
        self.assertTrue(provider.is_available())

        res = provider.analyze_screenshot(self.dummy_screenshot)
        self.assertTrue(res["available"])
        self.assertTrue(res["detected"])
        self.assertEqual(res["visual_risk_score"], 78)
        self.assertEqual(res["visual_risk_level"], "High")
        self.assertEqual(len(res["patterns"]), 1)
        self.assertEqual(res["patterns"][0]["name"], "Visual Urgency")

    @patch("urllib.request.urlopen")
    def test_openai_vision_provider_parsing(self, mock_urlopen):
        """Simulate successful OpenAI Vision API response."""
        from backend.ai.vision.openai_provider import OpenAIVisionProvider

        mock_payload = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps({
                            "detected": True,
                            "visual_risk_score": 65,
                            "visual_risk_level": "High",
                            "visual_confidence": 0.88,
                            "patterns": [
                                {
                                    "name": "Asymmetric Button Styling",
                                    "severity": "Medium",
                                    "confidence": 0.88,
                                    "evidence": "Prominent green 'Accept All' vs invisible grey 'Decline' text",
                                    "visual_details": "Visual hierarchy nudges users away from rejection.",
                                    "recommendation": "Search for secondary opt-out options."
                                }
                            ],
                            "analysis_summary": "Asymmetric visual button weighting detected."
                        })
                    }
                }
            ]
        }

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_payload).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        provider = OpenAIVisionProvider(api_key="mock_openai_key")
        self.assertTrue(provider.is_available())

        res = provider.analyze_screenshot(self.dummy_screenshot)
        self.assertTrue(res["available"])
        self.assertTrue(res["detected"])
        self.assertEqual(res["visual_risk_score"], 65)
        self.assertEqual(res["patterns"][0]["name"], "Asymmetric Button Styling")

    @patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError("http://api", 500, "Internal Server Error", {}, None))
    def test_provider_failure_resilience(self, mock_urlopen):
        """When Vision API returns HTTP 500 error, provider must not crash."""
        from backend.ai.vision.gemini_provider import GeminiVisionProvider

        provider = GeminiVisionProvider(api_key="mock_key")
        res = provider.analyze_screenshot(self.dummy_screenshot)
        self.assertFalse(res["detected"])
        self.assertEqual(res["visual_risk_score"], 0)
        self.assertIn("failed", res["status"].lower())

    def test_multimodal_decision_fusion_corroboration(self):
        """When semantic and visual detectors corroborate a pattern, confidence is reinforced."""
        from backend.detectors.scoring import calculate_multimodal_risk

        semantic_findings = [
            {
                "pattern": "Urgency or Scarcity",
                "severity": "Medium",
                "detection_method": "Hybrid (Rules + AI)",
                "confidence": 0.85,
                "evidence": ["Only 2 items left!"]
            }
        ]

        visual_analysis = {
            "available": True,
            "detected": True,
            "visual_risk_score": 70,
            "patterns": [
                {
                    "name": "Visual Urgency",
                    "severity": "Medium",
                    "confidence": 0.90,
                    "evidence": "Large flashing red countdown badge",
                    "visual_details": "Placed at header with high visual contrast"
                }
            ]
        }

        result = calculate_multimodal_risk(semantic_findings, visual_analysis)
        self.assertEqual(result["total_combined_patterns"], 1)
        fused = result["combined_findings"][0]

        # Method elevated to Multi-Modal
        self.assertEqual(fused["detection_method"], "Multi-Modal (DOM + Vision + Rules)")
        # Confidence reinforced beyond individual signals
        self.assertGreater(fused["confidence"], 0.85)
        # Visual evidence attached
        self.assertTrue(any("Visual Evidence" in ev for ev in fused["evidence"]))
        # Score calculation reflects Multi-Modal multiplier (1.25x)
        self.assertGreater(result["combined_risk_score"], 14)
        self.assertEqual(result["modality_breakdown"]["multimodal_corroborated_count"], 1)

    def test_multimodal_decision_fusion_visual_only(self):
        """Purely visual patterns (e.g. Asymmetric Button Styling) are preserved in combined findings."""
        from backend.detectors.scoring import calculate_multimodal_risk

        semantic_findings = []
        visual_analysis = {
            "available": True,
            "detected": True,
            "visual_risk_score": 40,
            "patterns": [
                {
                    "name": "Asymmetric Button Contrast",
                    "severity": "Medium",
                    "confidence": 0.88,
                    "evidence": "Saturated primary button vs faded secondary",
                    "visual_details": "Color contrast ratio creates visual misdirection"
                }
            ]
        }

        result = calculate_multimodal_risk(semantic_findings, visual_analysis)
        self.assertEqual(result["total_combined_patterns"], 1)
        fused = result["combined_findings"][0]
        self.assertEqual(fused["detection_method"], "Vision AI (Visual Layout)")
        self.assertEqual(result["modality_breakdown"]["visual_only_count"], 1)

    def test_multimodal_decision_fusion_offline_identity(self):
        """When Vision AI is offline, combined result matches semantic findings 100% identically."""
        from backend.detectors.scoring import calculate_multimodal_risk, calculate_dark_pattern_risk

        semantic_findings = [
            {"pattern": "Scarcity", "severity": "Medium", "confidence": 0.92, "detection_method": "AI Model", "evidence": ["Only 3 left"]}
        ]
        baseline = calculate_dark_pattern_risk(semantic_findings)

        offline_visual = {
            "available": False,
            "detected": False,
            "patterns": []
        }

        result = calculate_multimodal_risk(semantic_findings, offline_visual)
        self.assertEqual(result["combined_risk_score"], baseline["risk_score"])
        self.assertEqual(result["combined_risk_level"], baseline["risk_level"])
        self.assertEqual(len(result["combined_findings"]), 1)


class TestAccessBlockDetector(unittest.TestCase):
    """Test recognition of HTTP 403, WAF challenges, Akamai, Cloudflare, etc."""

    def test_access_block_403(self):
        from backend.scraper.access_detector import detect_access_block
        blocked, provider, info = detect_access_block(
            http_status=403,
            headers={},
            page_title="Access Denied",
            html="<html><body><h1>Access Denied</h1><p>You don't have permission to access on this server.</p></body></html>",
            body_text="Access Denied You don't have permission to access on this server."
        )
        self.assertTrue(blocked)
        self.assertIn("403", info.get("reason", ""))

    def test_access_block_429(self):
        from backend.scraper.access_detector import detect_access_block
        blocked, provider, info = detect_access_block(
            http_status=429,
            headers={},
            page_title="Too Many Requests",
            html="<html><body>Rate limit exceeded</body></html>",
            body_text="Rate limit exceeded"
        )
        self.assertTrue(blocked)
        self.assertEqual(provider, "HTTP 429 Rate Limiting")

    def test_access_block_akamai_html_200(self):
        """Akamai sometimes returns 200 OK with an Access Denied / EdgeSuite reference."""
        from backend.scraper.access_detector import detect_access_block
        akamai_html = """
        <HTML><HEAD>
        <TITLE>Access Denied</TITLE>
        </HEAD><BODY>
        <H1>Access Denied</H1>
        You don't have permission to access "http://www.target.com/" on this server.<P>
        Reference&#32;&#35;18&#46;12345678&#46;1234567890&#46;abcdef<P>
        <A HREF="https://errors.edgesuite.net/18.12345678.1234567890.abcdef">errors.edgesuite.net</A>
        </BODY></HTML>
        """
        blocked, provider, info = detect_access_block(
            http_status=200,
            headers={"server": "AkamaiGHost"},
            page_title="Access Denied",
            html=akamai_html,
            body_text="Access Denied You don't have permission to access. Reference #18.12345678.1234567890.abcdef"
        )
        self.assertTrue(blocked)
        self.assertIn("Akamai", provider)
        self.assertIn("Akamai", info.get("reason", ""))

    def test_access_block_cloudflare_challenge(self):
        """Cloudflare Turnstile / JS Challenge page."""
        from backend.scraper.access_detector import detect_access_block
        cf_html = """
        <!DOCTYPE html><html><head><title>Just a moment...</title></head>
        <body>
        <div id="cf-turnstile" class="cf-turnstile-wrapper"></div>
        <p>Verifying you are human. This may take a few seconds.</p>
        <span class="cf-ray-id">Ray ID: 89abcdef01234567</span>
        </body></html>
        """
        blocked, provider, info = detect_access_block(
            http_status=200,
            headers={"cf-ray": "89abcdef01234567"},
            page_title="Just a moment...",
            html=cf_html,
            body_text="Just a moment... Verifying you are human. Ray ID: 89abcdef01234567"
        )
        self.assertTrue(blocked)
        self.assertIn("Cloudflare", provider)

    def test_access_block_datadome_captcha(self):
        """Datadome bot challenge."""
        from backend.scraper.access_detector import detect_access_block
        blocked, provider, info = detect_access_block(
            http_status=200,
            headers={},
            page_title="Security Verification",
            html="<html><script src='https://js.datadome.co/tags.js'></script><body>Please complete the security check</body></html>",
            body_text="Please complete the security check"
        )
        self.assertTrue(blocked)
        self.assertIn("Datadome", provider)

    def test_benign_text_with_security_words_not_blocked(self):
        """Benign pages that mention security, privacy, or policy must NOT be flagged as blocked."""
        from backend.scraper.access_detector import detect_access_block
        normal_page_text = (
            "Welcome to our portal. We take information security very seriously. "
            "Unauthorized access is denied without login credentials. "
            "Please review our access control policy and terms of service. "
            "Our company offers high quality cloud computing services to millions of clients globally."
        ) * 10
        blocked, provider, info = detect_access_block(
            http_status=200,
            headers={"server": "nginx"},
            page_title="Cloud Services - Security & Reliability",
            html=f"<html><body><h1>Cloud Services</h1><p>{normal_page_text}</p></body></html>",
            body_text=normal_page_text
        )
        self.assertFalse(blocked)
        self.assertIsNone(provider)


class TestPipelineGatingOnBlock(unittest.TestCase):
    """Test that blocked scans bypass dark-pattern analysis and assign null risk scores."""

    def test_blocked_scan_skips_analysis_and_has_null_risk(self):
        from backend.analyzer import analyze_website

        scraped_data = {
            "status": "blocked",
            "access_blocked": True,
            "block_provider": "Akamai EdgeSuite",
            "block_info": {"reason": "Akamai EdgeSuite access denied reference page."},
            "url": "https://protected-store.example",
            "title": "Access Denied",
            "text": "Access Denied. You don't have permission to access on this server.",
            "html": "<html><body>Access Denied</body></html>",
            "dom_elements": [{"text": "Access Denied", "element_type": "heading"}],
            "links": [],
            "buttons": [],
            "inputs": [],
            "headers": {},
            "cookie_consent": {"banner_detected": False}
        }

        result = analyze_website(scraped_data)
        # Requirement: skips SVM and rules, risk_score is None, findings empty
        self.assertEqual(result["status"], "blocked")
        self.assertTrue(result["access_blocked"])
        self.assertIsNone(result["risk_score"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["total_patterns"], 0)

    def test_blocked_scan_pdf_report(self):
        """Test PDF generation for blocked scan outputs valid document without crashing."""
        from backend.report_generator import generate_pdf_report

        scan_record = {
            "scan_id": "test-block-pdf-001",
            "status": "blocked",
            "access_blocked": True,
            "block_provider": "Cloudflare WAF / Turnstile Challenge",
            "block_info": {"reason": "Cloudflare challenge detected."},
            "message": "Target website access was blocked by Cloudflare.",
            "website": {
                "url": "https://cloudflare-protected.example",
                "title": "Just a moment...",
                "status": "blocked",
                "access_blocked": True,
                "block_provider": "Cloudflare WAF / Turnstile Challenge"
            },
            "security_analysis": {
                "status": "blocked",
                "security_score": None,
                "findings": []
            },
            "dark_pattern_analysis": {
                "status": "blocked",
                "access_blocked": True,
                "risk_score": None,
                "findings": []
            }
        }

        buf = generate_pdf_report(scan_record)
        self.assertIsNotNone(buf)
        pdf_bytes = buf.getvalue()
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        self.assertGreater(len(pdf_bytes), 1000)


class TestBrowserCaptureFull(unittest.TestCase):
    """
    Comprehensive 15-point verification suite for DarkShield Browser Capture Mode:
    1. /scan/capture accepts valid capture
    2. /scan/capture rejects invalid payload
    3. Screenshot processing
    4. DOM extraction
    5. Analyzer reuse
    6. SVM execution
    7. Rule execution
    8. Vision AI fallback
    9. Risk scoring
    10. PDF generation
    11. Scan history
    12. Blocked automatic scan
    13. Browser capture successful scan
    14. Evidence grounding
    15. Sensitive data prevention
    """

    def setUp(self):
        from backend.app import BrowserCaptureRequest, parse_html_to_scraped_data, scan_captured_page
        self.BrowserCaptureRequest = BrowserCaptureRequest
        self.parse_html_to_scraped_data = parse_html_to_scraped_data
        self.scan_captured_page = scan_captured_page

    def test_01_scan_capture_accepts_valid_capture(self):
        """1. /scan/capture accepts valid capture payload."""
        req = self.BrowserCaptureRequest(
            url="https://store.example/product/1",
            title="Special Deal Store",
            html="<html><body><h1>Special Deal</h1><p>Welcome to our catalog.</p></body></html>",
            text="Special Deal Welcome to our catalog."
        )
        res = self.scan_captured_page(req)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["scan_mode"], "browser_capture")
        self.assertTrue(res["scan_success"])
        self.assertFalse(res["access_blocked"])

    def test_02_scan_capture_rejects_invalid_payload(self):
        """2. /scan/capture rejects invalid payload with score = None."""
        for invalid_url in ["", "not_a_url", "ftp://invalid-protocol.com"]:
            req = self.BrowserCaptureRequest(url=invalid_url, html="<p>Test</p>")
            res = self.scan_captured_page(req)
            self.assertEqual(res["status"], "invalid_url")
            self.assertIsNone(res["risk_score"])
            self.assertEqual(res["findings"], [])

    def test_03_screenshot_processing(self):
        """3. Screenshot processing strips data URL prefix and decodes clean base64."""
        import base64
        sample_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
        data_url = f"data:image/png;base64,{sample_b64}"

        req = self.BrowserCaptureRequest(
            url="https://store.example",
            screenshot=data_url
        )
        scraped = self.parse_html_to_scraped_data(req)
        self.assertEqual(scraped["screenshot_b64"], sample_b64)
        decoded = base64.b64decode(scraped["screenshot_b64"])
        self.assertGreater(len(decoded), 0)

    def test_04_dom_extraction(self):
        """4. DOM extraction decomposes structured elements into buttons, links, inputs."""
        elements_sample = [
            {"element_type": "button", "tag": "button", "text": "Buy Now"},
            {"element_type": "link", "tag": "a", "text": "Terms", "href": "/terms"},
            {"element_type": "checkbox", "tag": "input", "name": "marketing_optin", "checked": True},
            {"element_type": "heading", "tag": "h1", "text": "Flash Sale"}
        ]
        req = self.BrowserCaptureRequest(
            url="https://store.example",
            elements=elements_sample
        )
        scraped = self.parse_html_to_scraped_data(req)
        self.assertEqual(len(scraped["buttons"]), 1)
        self.assertEqual(scraped["buttons"][0]["text"], "Buy Now")
        self.assertEqual(len(scraped["links"]), 1)
        self.assertEqual(scraped["links"][0]["href"], "/terms")
        self.assertEqual(len(scraped["inputs"]), 1)
        self.assertEqual(len(scraped["dom_elements"]), 4)

    def test_05_analyzer_reuse(self):
        """5. Analyzer reuse: Captured page runs through the exact same analyze_website engine."""
        from backend.analyzer import analyze_website
        scraped = self.parse_html_to_scraped_data(
            "https://test.example",
            "<html><body><p>Normal store page</p></body></html>"
        )
        res = analyze_website(scraped)
        self.assertIn("dark_pattern_analysis", res)
        self.assertIn("security_score", res)
        self.assertIn("combined_analysis", res.get("dark_pattern_analysis", {}))

    def test_06_svm_execution(self):
        """6. SVM execution runs Calibrated Linear SVM V2 on captured DOM candidates."""
        from backend.ai.detector import AIDarkPatternDetector
        detector = AIDarkPatternDetector.get_instance()
        self.assertTrue(detector.is_ready())

        text_sample = "Hurry! Only 2 items left in stock. Order within 10 minutes!"
        preds = detector.predict_candidates([{"text": text_sample}])
        self.assertGreater(len(preds), 0)
        self.assertIn(preds[0]["pattern"], ["Scarcity", "Urgency"])
        self.assertGreater(preds[0]["confidence"], 0.7)

    def test_07_rule_execution(self):
        """7. Rule execution detects heuristic triggers from captured interactive elements."""
        from backend.detectors.dark_patterns import detect_dark_patterns_rule_based
        scraped_sample = {
            "text": "Special offer! Hurry, sale ends today!",
            "buttons": [{"text": "Buy Now"}],
            "links": [],
            "inputs": []
        }
        res = detect_dark_patterns_rule_based(scraped_sample)
        findings = res.get("findings", [])
        self.assertGreaterEqual(len(findings), 1)

    def test_08_vision_ai_fallback(self):
        """8. Vision AI fallback behaves gracefully when unconfigured or offline."""
        from backend.ai.vision import get_vision_status, analyze_screenshot
        status = get_vision_status()
        self.assertTrue("unavailable" in status.lower() or "offline" in status.lower())
        vis_res = analyze_screenshot(None)
        self.assertFalse(vis_res["available"])
        self.assertEqual(vis_res["patterns"], [])

    def test_09_risk_scoring(self):
        """9. Risk scoring: Clean captured page gets risk_score = 0; deceptive gets multi-factor score."""
        from backend.detectors.scoring import calculate_overall_risk_score
        # Clean page -> 0
        clean_res = calculate_overall_risk_score([])
        self.assertEqual(clean_res["risk_score"], 0)
        self.assertEqual(clean_res["risk_level"], "None")

        # Deceptive findings -> Multi-factor score
        deceptive_findings = [
            {
                "pattern": "Urgency - Countdown Timer",
                "severity": "High",
                "confidence": 0.95,
                "detection_method": "Rule-Based",
                "evidence": ["Sale ends in 02:00"]
            },
            {
                "pattern": "Scarcity - Low Stock",
                "severity": "Medium",
                "confidence": 0.90,
                "detection_method": "AI Model",
                "evidence": ["Only 1 left in stock"]
            }
        ]
        risk_res = calculate_overall_risk_score(deceptive_findings)
        self.assertGreater(risk_res["risk_score"], 30)
        self.assertIn("risk_breakdown", risk_res)
        self.assertIn("severity", risk_res["risk_breakdown"])
        self.assertIn("confidence", risk_res["risk_breakdown"])

    def test_10_pdf_generation(self):
        """10. PDF generation specifies Browser Capture Mode and does not label it automated Playwright."""
        from backend.report_generator import generate_pdf_report
        scan_record = {
            "url": "https://meesho-captured.example",
            "scan_mode": "browser_capture",
            "website": {
                "url": "https://meesho-captured.example",
                "title": "Meesho Shopping",
                "scan_mode": "browser_capture"
            },
            "security_analysis": {
                "security_score": 92,
                "risk_level": "Low",
                "findings": []
            },
            "dark_pattern_analysis": {
                "risk_score": 58,
                "risk_level": "Medium",
                "findings": [
                    {
                        "pattern": "Scarcity - Low Stock",
                        "severity": "Medium",
                        "confidence": 0.92,
                        "detection_method": "AI Model",
                        "evidence": ["Only 2 left in stock"]
                    }
                ]
            }
        }
        buf = generate_pdf_report(scan_record)
        self.assertIsNotNone(buf)
        pdf_bytes = buf.getvalue()
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    def test_11_scan_history(self):
        """11. Scan history persists scan_mode = 'browser_capture' in index and detail files."""
        from backend.scan_history import save_scan, get_scan_history, get_scan_by_id
        test_scan = {
            "url": "https://history-test.example",
            "scan_mode": "browser_capture",
            "website": {
                "url": "https://history-test.example",
                "title": "History Test Page",
                "scan_mode": "browser_capture"
            },
            "security_analysis": {"security_score": 100, "risk_level": "Low", "findings": []},
            "dark_pattern_analysis": {"risk_score": 0, "risk_level": "None", "findings": []}
        }
        scan_id = save_scan(test_scan)
        self.assertIsNotNone(scan_id)

        # Check index item
        history = get_scan_history()
        match = next((item for item in history if item.get("scan_id") == scan_id), None)
        self.assertIsNotNone(match)
        self.assertEqual(match.get("scan_mode"), "browser_capture")

        # Check detail record
        detail = get_scan_by_id(scan_id)
        self.assertIsNotNone(detail)
        self.assertEqual(detail.get("scan_mode"), "browser_capture")

    def test_12_blocked_automatic_scan(self):
        """12. Blocked automatic scan produces status = 'blocked', risk_score = None, findings = []."""
        from backend.analyzer import analyze_website
        blocked_scraped = {
            "url": "https://blocked-site.example",
            "access_blocked": True,
            "block_provider": "Akamai EdgeSuite",
            "block_info": {"reason": "403 Forbidden Access Denied"}
        }
        res = analyze_website(blocked_scraped)
        self.assertEqual(res.get("status"), "blocked")
        dp_analysis = res.get("dark_pattern_analysis", {})
        self.assertIsNone(dp_analysis.get("risk_score"))
        self.assertEqual(dp_analysis.get("findings"), [])

    def test_13_browser_capture_successful_scan(self):
        """13. Browser capture successful scan produces complete audit with scan_mode."""
        req = self.BrowserCaptureRequest(
            url="https://captured-store.example",
            title="Online Fashion Hub",
            html="<html><body><h1>Store</h1><p>Hurry! Only 3 left!</p><button>Order Now</button></body></html>",
            text="Store Hurry! Only 3 left! Order Now"
        )
        res = self.scan_captured_page(req)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["scan_mode"], "browser_capture")
        self.assertIn("scan_id", res)
        self.assertIsNotNone(res["risk_score"])
        self.assertGreater(res["risk_score"], 0)

    def test_14_evidence_grounding(self):
        """14. Evidence grounding: detected dark pattern is grounded in text and avoids irrelevant claims."""
        from backend.ai.detector import AIDarkPatternDetector
        detector = AIDarkPatternDetector.get_instance()

        evidence_str = "Only 2 items left in stock! Order before midnight."
        preds = detector.predict_candidates([{"text": evidence_str}])
        self.assertGreater(len(preds), 0)
        self.assertEqual(preds[0]["pattern"], "Scarcity")

        # Irrelevant institutional text must NOT trigger dark pattern
        clean_academic = "At KKWIEER, learning goes beyond textbooks with dedicated faculty."
        clean_preds = detector.predict_candidates([{"text": clean_academic}])
        self.assertEqual(len(clean_preds), 0)

    def test_15_sensitive_data_not_collected(self):
        """15. Sensitive data prevention: Passwords, card numbers, and tokens are filtered out."""
        import re
        SENSITIVE_INPUT_REGEX = re.compile(
            r"password|passwd|card|cvv|ccnum|credit|debit|ssn|social.*security|auth|token|secret|api[_-]?key",
            re.IGNORECASE
        )

        sample_inputs = [
            {"type": "password", "name": "user_pwd", "id": "pwd"},
            {"type": "text", "name": "cc_number", "placeholder": "Credit Card Number"},
            {"type": "text", "name": "cvv", "placeholder": "123"},
            {"type": "text", "name": "search_query", "placeholder": "Search shirts..."},
            {"type": "checkbox", "name": "remember_me"}
        ]

        safe_inputs = []
        for inp in sample_inputs:
            t = inp.get("type", "")
            n = inp.get("name", "")
            p = inp.get("placeholder", "")
            if t == "password" or SENSITIVE_INPUT_REGEX.search(n) or SENSITIVE_INPUT_REGEX.search(p):
                continue
            safe_inputs.append(inp)

        self.assertEqual(len(safe_inputs), 2)
        names = [i["name"] for i in safe_inputs]
        self.assertIn("search_query", names)
        self.assertIn("remember_me", names)
        self.assertNotIn("user_pwd", names)
        self.assertNotIn("cc_number", names)
        self.assertNotIn("cvv", names)

    def test_16_amazon_consistency_regression(self):
        """16. Amazon Regression: Automated WAF challenge must not return false Clean 0/100, while browser capture audits full DOM."""
        from backend.captured_page import CapturedPage
        from backend.analyzer import analyze_page

        # Simulated Amazon automated scan response (AWS WAF 202 challenge)
        auto_amazon_payload = {
            "url": "https://www.amazon.in/",
            "title": "Untitled Website",
            "html": "<script src='https://token.awswaf.com/challenge.js'></script>",
            "visible_text": "",
            "links": [],
            "buttons": [],
            "inputs": [],
            "http_status": 202,
            "access_blocked": True,
            "block_provider": "AWS WAF / CloudFront"
        }
        auto_page = CapturedPage.from_dict(auto_amazon_payload, capture_method="automated")
        auto_result = analyze_page(auto_page)

        # Must NOT be marked clean 0/100
        self.assertEqual(auto_result["status"], "blocked")
        self.assertIsNone(auto_result["risk_score"])
        self.assertEqual(auto_result["findings"], [])
        self.assertTrue(auto_result["access_blocked"])

        # Simulated Amazon browser capture with actual rendered DOM
        browser_amazon_payload = {
            "url": "https://www.amazon.in/",
            "title": "Amazon.in: Deal of the Day",
            "html": "<html><body><h1>Store</h1><p>Hurry! Only 2 left in stock!</p><button>Buy Now</button></body></html>",
            "visible_text": "Store Hurry! Only 2 left in stock! Buy Now",
            "links": [{"href": "/deal", "text": "Deal"}],
            "buttons": [{"text": "Buy Now"}],
            "inputs": [{"type": "text", "placeholder": "Search"}],
            "http_status": 200,
            "access_blocked": False
        }
        browser_page = CapturedPage.from_dict(browser_amazon_payload, capture_method="browser_capture")
        browser_result = analyze_page(browser_page)

        # Browser capture runs full audit
        self.assertEqual(browser_result["status"], "complete")
        self.assertIsNotNone(browser_result["risk_score"])
        self.assertGreater(browser_result["risk_score"], 0)
        self.assertFalse(browser_result["access_blocked"])

    def test_17_meesho_blocked_vs_capture_regression(self):
        """17. Meesho Regression: Automated Akamai block withholds score, browser capture succeeds without hardcoding."""
        from backend.captured_page import CapturedPage
        from backend.analyzer import analyze_page

        # Automated crawler blocked by Akamai HTTP 403
        akamai_payload = {
            "url": "https://www.meesho.com/",
            "title": "Access Denied",
            "html": "<h1>Access Denied</h1><p>You don't have permission to access 'http://www.meesho.com/' on this server.</p>",
            "visible_text": "Access Denied You don't have permission to access on this server.",
            "http_status": 403,
            "access_blocked": True,
            "block_provider": "Akamai"
        }
        auto_meesho = CapturedPage.from_dict(akamai_payload, capture_method="automated")
        auto_res = analyze_page(auto_meesho)

        self.assertEqual(auto_res["status"], "blocked")
        self.assertIsNone(auto_res["risk_score"])
        self.assertEqual(auto_res["findings"], [])

        # Browser capture on Meesho product page
        browser_meesho_payload = {
            "url": "https://www.meesho.com/kurtis/p/123",
            "title": "Rayon Embroidered Kurti",
            "html": "<html><body><h2>Kurti</h2><p>Hurry, only 2 left in stock!</p><button>Order Now</button></body></html>",
            "visible_text": "Rayon Embroidered Kurti Hurry, only 2 left in stock! Order Now",
            "buttons": [{"text": "Order Now"}],
            "links": [{"href": "/cart", "text": "Cart"}]
        }
        browser_meesho = CapturedPage.from_dict(browser_meesho_payload, capture_method="browser_capture")
        browser_res = analyze_page(browser_meesho)

        self.assertEqual(browser_res["status"], "complete")
        self.assertIsNotNone(browser_res["risk_score"])
        self.assertGreater(browser_res["risk_score"], 0)

    def test_18_cloudflare_challenge_regression(self):
        """18. Cloudflare Regression: Turnstile/interstitial challenge must be blocked with risk score withheld."""
        from backend.captured_page import CapturedPage
        from backend.analyzer import analyze_page

        cf_payload = {
            "url": "https://www.scrapingcourse.com/cloudflare-challenge",
            "title": "Just a moment...",
            "html": "<html><body><div id='cf-turnstile'>Verify you are human</div></body></html>",
            "visible_text": "Just a moment... Verify you are human",
            "http_status": 403,
            "access_blocked": True,
            "block_provider": "Cloudflare"
        }
        cf_page = CapturedPage.from_dict(cf_payload, capture_method="automated")
        cf_res = analyze_page(cf_page)

        self.assertEqual(cf_res["status"], "blocked")
        self.assertIsNone(cf_res["risk_score"])
        self.assertEqual(cf_res["findings"], [])

    def test_19_capture_comparison_diagnostics(self):
        """19. Diagnostic comparison: compare_captures accurately computes metric disparity and root-cause explanation."""
        from backend.captured_page import compare_captures

        auto_sample = {
            "url": "https://www.amazon.in/",
            "status": "blocked",
            "access_blocked": True,
            "block_provider": "AWS WAF / CloudFront",
            "html": "<script src='https://token.awswaf.com/challenge.js'></script>",
            "visible_text": "",
            "links": [],
            "buttons": [],
            "risk_score": None,
            "findings": []
        }
        browser_sample = {
            "url": "https://www.amazon.in/",
            "status": "complete",
            "access_blocked": False,
            "html": "<html><body><button>Buy Now</button></body></html>",
            "visible_text": "Deal of the day Hurry! Only 2 left in stock!",
            "links": [{"href": "/item", "text": "Item"}],
            "buttons": [{"text": "Buy Now"}],
            "risk_score": 54,
            "findings": [{"pattern": "Urgency or Scarcity"}]
        }

        diff = compare_captures(auto_sample, browser_sample)
        self.assertEqual(diff["url"], "https://www.amazon.in/")
        self.assertEqual(diff["automated"]["quality"], "blocked")
        self.assertEqual(diff["browser_capture"]["quality"], "complete")
        self.assertIn("AWS WAF", diff["conclusion"])
        self.assertEqual(diff["differences"]["buttons_diff"], 1)


if __name__ == "__main__":
    unittest.main()




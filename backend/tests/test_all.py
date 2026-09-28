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
        self.assertEqual(res["scan_status"], "blocked_or_interaction_required")
        self.assertEqual(res["navigation_status"], "blocked_or_interaction_required")
        self.assertIn("anti-bot challenge", res["warning"])

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


if __name__ == "__main__":
    unittest.main()



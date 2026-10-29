"""
Unit & Integration Tests for DarkShield AI Chrome Extension
============================================================

Tests:
1. Manifest V3 validation (permissions, service worker, popup action)
2. Popup HTML elements validation (dual buttons, config panel, progress, audit list)
3. Content script DOM & link extraction rules
4. Background script crawl safety filters (destructive links, tracking params, static files)
5. Full browser-driven crawl API simulation (start, multi-page submit, status, finish, PDF)
"""

import os
import re
import json
import unittest

from backend.app import (
    BrowserWebsiteScanStartRequest,
    BrowserWebsitePageSubmission,
    BrowserWebsiteScanFinishRequest,
    start_browser_website_scan,
    submit_browser_website_page,
    get_website_scan_status,
    get_website_scanned_pages,
    finish_browser_website_scan,
    get_website_pdf_report,
)
from backend.website_history import delete_website_scan

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXTENSION_DIR = os.path.join(BASE_DIR, "browser_extension")


class TestExtensionManifest(unittest.TestCase):
    """Verifies Chrome Extension Manifest V3 configuration and permissions."""

    def setUp(self):
        self.manifest_path = os.path.join(EXTENSION_DIR, "manifest.json")
        self.assertTrue(os.path.exists(self.manifest_path), "manifest.json must exist in browser_extension/")
        with open(self.manifest_path, "r", encoding="utf-8") as f:
            self.manifest = json.load(f)

    def test_manifest_version(self):
        self.assertEqual(self.manifest.get("manifest_version"), 3)

    def test_required_permissions(self):
        perms = set(self.manifest.get("permissions", []))
        self.assertIn("activeTab", perms)
        self.assertIn("scripting", perms)
        self.assertIn("tabs", perms, "tabs permission required for dedicated scan tab management")
        self.assertIn("storage", perms, "storage permission required to persist crawl progress across popup toggling")

    def test_popup_and_background_worker(self):
        self.assertEqual(self.manifest.get("action", {}).get("default_popup"), "popup.html")
        self.assertEqual(self.manifest.get("background", {}).get("service_worker"), "background.js")

    def test_host_permissions(self):
        hosts = set(self.manifest.get("host_permissions", []))
        self.assertTrue("<all_urls>" in hosts or "*://*/*" in hosts, "Host permissions must allow script execution on target webpages")


class TestExtensionPopupUI(unittest.TestCase):
    """Verifies that popup.html contains both scanning options and all crawl controls."""

    def setUp(self):
        self.popup_path = os.path.join(EXTENSION_DIR, "popup.html")
        self.assertTrue(os.path.exists(self.popup_path), "popup.html must exist in browser_extension/")
        with open(self.popup_path, "r", encoding="utf-8") as f:
            self.html = f.read()

    def test_dual_action_buttons_present(self):
        """Verifies both 'Analyze Current Page' and 'Scan Whole Website' buttons exist."""
        self.assertIn('id="btn-analyze"', self.html)
        self.assertIn('Analyze Current Page', self.html)

        self.assertIn('id="btn-whole-website-toggle"', self.html)
        self.assertIn('Scan Whole Website', self.html)

        # Check button order: btn-analyze should appear before btn-whole-website-toggle
        idx_analyze = self.html.find('id="btn-analyze"')
        idx_whole = self.html.find('id="btn-whole-website-toggle"')
        self.assertTrue(idx_analyze < idx_whole, "'Scan Whole Website' button must appear below 'Analyze Current Page'")

    def test_whole_website_config_panel(self):
        """Verifies max pages, depth selectors, start, and cancel buttons exist."""
        self.assertIn('id="whole-site-panel"', self.html)
        self.assertIn('id="select-max-pages"', self.html)
        self.assertIn('id="select-max-depth"', self.html)
        self.assertIn('id="btn-start-site-scan"', self.html)
        self.assertIn('id="btn-cancel-site-scan"', self.html)

        # Check max page options
        self.assertIn('value="20"', self.html)
        self.assertIn('value="50"', self.html)
        self.assertIn('value="100"', self.html)

    def test_page_by_page_audit_section(self):
        """Verifies elements for rendering multi-page audit list and progress stats."""
        self.assertIn('id="site-progress-section"', self.html)
        self.assertIn('id="site-stat-discovered"', self.html)
        self.assertIn('id="site-stat-scanned"', self.html)
        self.assertIn('id="site-stat-blocked"', self.html)
        self.assertIn('id="site-current-url"', self.html)
        self.assertIn('id="site-results-section"', self.html)
        self.assertIn('id="site-pages-list"', self.html)


class TestExtensionScriptsSafety(unittest.TestCase):
    """Verifies background and content scripts implement safety checks."""

    def test_background_script_filters(self):
        bg_path = os.path.join(EXTENSION_DIR, "background.js")
        with open(bg_path, "r", encoding="utf-8") as f:
            bg_code = f.read()

        # Check for tracking param normalization
        self.assertIn("utm_source", bg_code)
        self.assertIn("gclid", bg_code)

        # Check for destructive path exclusion
        self.assertIn("logout", bg_code)
        self.assertIn("delete", bg_code)

        # Check for static file extension exclusion
        self.assertIn(".pdf", bg_code)
        self.assertIn(".jpg", bg_code)

        # Check for background scan tab management
        self.assertIn("chrome.tabs.create", bg_code)
        self.assertIn("chrome.tabs.remove", bg_code)
        self.assertIn("preAssignedScanId", bg_code)
        self.assertIn("SCAN_FAILED", bg_code)

    def test_popup_preflight_and_error_propagation(self):
        popup_path = os.path.join(EXTENSION_DIR, "popup.js")
        with open(popup_path, "r", encoding="utf-8") as f:
            popup_code = f.read()

        # Check for direct pre-flight start call
        self.assertIn("/scan/website/browser/start", popup_code)
        self.assertIn("allow_local: true", popup_code)

        # Check for explicit HTTP status error handling
        self.assertIn("HTTP 404", popup_code)
        self.assertIn("HTTP 400", popup_code)
        self.assertIn("HTTP 500", popup_code)
        self.assertIn("Failed to fetch", popup_code)

        # Check for SCAN_FAILED listener handling
        self.assertIn("SCAN_FAILED", popup_code)

    def test_content_script_privacy_and_links(self):
        cs_path = os.path.join(EXTENSION_DIR, "content.js")
        with open(cs_path, "r", encoding="utf-8") as f:
            cs_code = f.read()

        # Privacy filter for passwords and credentials
        self.assertIn("password", cs_code)
        self.assertIn("credit", cs_code)

        # Discovered links extraction for whole website crawler
        self.assertIn("discovered_links", cs_code)


class TestBrowserScanApiSimulation(unittest.TestCase):
    """Simulates the entire extension whole-website scan cycle."""

    def setUp(self):
        self.created_scans = []

    def tearDown(self):
        for sid in self.created_scans:
            try:
                delete_website_scan(sid)
            except Exception:
                pass

    def test_full_extension_scan_cycle(self):
        # 1. Start scan
        start_req = BrowserWebsiteScanStartRequest(
            url="https://example.com",
            max_pages=5,
            max_depth=2,
            allow_subdomains=False
        )
        res_start = start_browser_website_scan(start_req)
        scan_id = res_start["scan_id"]
        self.created_scans.append(scan_id)
        self.assertEqual(res_start["status"], "crawling")

        # 2. Submit Page 1: Homepage (Clean)
        page1_req = BrowserWebsitePageSubmission(
            url="https://example.com",
            title="Example Homepage",
            depth=0,
            html="<html><body><h1>Welcome to Example</h1><p>Transparent e-commerce platform.</p></body></html>",
            visible_text="Welcome to Example Transparent e-commerce platform.",
            elements=[
                {"element_type": "heading", "tag": "h1", "text": "Welcome to Example"}
            ],
            discovered_urls=["https://example.com/products", "https://example.com/checkout"]
        )
        res_p1 = submit_browser_website_page(scan_id, page1_req)
        self.assertEqual(res_p1["status"], "success")
        self.assertEqual(res_p1["page_id"], "page_1")
        self.assertEqual(res_p1["page_record"]["findings_count"], 0)

        # 3. Submit Page 2: Checkout (Urgency Dark Pattern)
        page2_req = BrowserWebsitePageSubmission(
            url="https://example.com/checkout",
            title="Checkout",
            depth=1,
            html="<html><body><p class='urgency-badge'>HURRY! ONLY 1 ITEM LEFT IN STOCK!</p></body></html>",
            visible_text="HURRY! ONLY 1 ITEM LEFT IN STOCK!",
            elements=[
                {"element_type": "text_block", "tag": "p", "text": "HURRY! ONLY 1 ITEM LEFT IN STOCK!"}
            ]
        )
        res_p2 = submit_browser_website_page(scan_id, page2_req)
        self.assertEqual(res_p2["status"], "success")
        self.assertEqual(res_p2["page_id"], "page_2")
        self.assertGreaterEqual(res_p2["page_record"]["findings_count"], 1)

        # 4. Check live status
        status_data = get_website_scan_status(scan_id)
        self.assertEqual(status_data["pages_scanned"], 2)

        # 5. Check pages list
        pages_data = get_website_scanned_pages(scan_id)
        self.assertEqual(len(pages_data["pages"]), 2)

        # 6. Finish scan
        finish_req = BrowserWebsiteScanFinishRequest(total_discovered=3)
        finish_data = finish_browser_website_scan(scan_id, finish_req)
        summary = finish_data["summary"]
        self.assertEqual(summary["scan_status"], "completed")
        self.assertEqual(summary["pages_scanned"], 2)
        self.assertGreater(summary["website_risk_score"], 0)

        # 7. Check PDF report download
        pdf_response = get_website_pdf_report(scan_id)
        self.assertIsNotNone(pdf_response)
        self.assertEqual(pdf_response.media_type, "application/pdf")
        self.assertIn("filename=", pdf_response.headers.get("content-disposition", ""))

    def test_bounded_link_discovery_and_max_pages_ceiling(self):
        """Verifies that discovered URLs are strictly bounded by max_pages even if 500+ links are found."""
        start_req = BrowserWebsiteScanStartRequest(
            url="https://ecommerce-example.com",
            max_pages=20,
            max_depth=2,
            allow_subdomains=False,
            allow_local=True
        )
        res_start = start_browser_website_scan(start_req)
        scan_id = res_start["scan_id"]
        self.addCleanup(lambda: delete_website_scan(scan_id))

        # Simulate initial page discovering 500 product links
        large_link_set = [f"https://ecommerce-example.com/product-{i}?color=red&sort=price" for i in range(500)]
        page1_req = BrowserWebsitePageSubmission(
            url="https://ecommerce-example.com",
            title="Massive Store Catalog",
            depth=0,
            html="<html><body><h1>Massive Store</h1></body></html>",
            visible_text="Massive Store with 500 products",
            elements=[],
            discovered_urls=large_link_set
        )
        submit_browser_website_page(scan_id, page1_req)

        # Check status snapshot: pages_discovered must NEVER exceed max_pages (20)
        status_data = get_website_scan_status(scan_id)
        self.assertLessEqual(status_data["pages_discovered"], 20, "Discovered count must be capped to max_pages at discovery time")
        self.assertEqual(status_data["pages_scanned"], 1)

        # Finish scan with large total_discovered: summary must cap to max_pages
        finish_req = BrowserWebsiteScanFinishRequest(total_discovered=589)
        finish_data = finish_browser_website_scan(scan_id, finish_req)
        summary = finish_data["summary"]
        self.assertLessEqual(summary["total_pages_discovered"], 20)

    def test_blocked_page_handling_never_reports_clean(self):
        """Verifies that blocked pages (WAF/Cloudflare/Akamai) are never reported as clean (0)."""
        start_req = BrowserWebsiteScanStartRequest(
            url="https://protected-site.com",
            max_pages=5,
            max_depth=1
        )
        res_start = start_browser_website_scan(start_req)
        scan_id = res_start["scan_id"]
        self.addCleanup(lambda: delete_website_scan(scan_id))

        # Submit Cloudflare blocked page
        blocked_req = BrowserWebsitePageSubmission(
            url="https://protected-site.com/blocked",
            title="Attention Required! | Cloudflare",
            depth=1,
            html="<html><body><h1>Please verify you are human</h1></body></html>",
            visible_text="Please verify you are human Cloudflare Ray ID",
            access_blocked=True,
            block_provider="Cloudflare"
        )
        res_p = submit_browser_website_page(scan_id, blocked_req)
        record = res_p["page_record"]

        self.assertTrue(record["access_blocked"])
        self.assertEqual(record["block_provider"], "Cloudflare")
        self.assertIsNone(record["risk_score"], "Blocked pages must have risk_score=None, not 0 (clean)")
        self.assertEqual(record["risk_level"], "Not Assessed")
        self.assertEqual(record["status"], "blocked")

        status_data = get_website_scan_status(scan_id)
        self.assertEqual(status_data["pages_blocked"], 1)

    def test_timed_out_page_submission_and_summary(self):
        """Verifies that timed-out pages reach terminal status and produce Insufficient Data summary if no valid pages exist."""
        start_req = BrowserWebsiteScanStartRequest(
            url="https://slow-site.com",
            max_pages=5,
            max_depth=1
        )
        res_start = start_browser_website_scan(start_req)
        scan_id = res_start["scan_id"]
        self.addCleanup(lambda: delete_website_scan(scan_id))

        # Submit timed_out page
        timed_out_req = BrowserWebsitePageSubmission(
            url="https://slow-site.com/slow-page",
            title="Slow Page",
            depth=1,
            html="",
            visible_text="",
            status="timed_out",
            message="Navigation timed out"
        )
        res_p = submit_browser_website_page(scan_id, timed_out_req)
        record = res_p["page_record"]

        self.assertEqual(record["status"], "timed_out")
        self.assertIsNone(record["risk_score"])

        status_data = get_website_scan_status(scan_id)
        self.assertEqual(status_data.get("pages_timed_out", 0), 1)

        finish_req = BrowserWebsiteScanFinishRequest(total_discovered=1)
        finish_data = finish_browser_website_scan(scan_id, finish_req)
        summary = finish_data["summary"]
        self.assertEqual(summary.get("pages_timed_out", 0), 1)
        self.assertTrue(summary["is_partial_scan"])
        self.assertIsNone(summary["website_risk_score"])
        self.assertEqual(summary["website_risk_level"], "Insufficient Data")


if __name__ == "__main__":
    unittest.main()


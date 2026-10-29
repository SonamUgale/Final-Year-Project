"""
Unit & Integration Tests for DarkShield AI Whole Website Scanning
==================================================================

Covers:
1. SSRF security & URL safety verification
2. URL normalization & tracking param removal
3. Internal domain detection & static/destructive link exclusion
4. Internal link extraction & relative URL resolution
5. BFS crawler limits (max pages, max depth, cancellation)
6. Website-wide summary aggregation & engineering risk indicator calculation
7. Multi-page PDF audit report generation
8. FastAPI Whole Website Scan endpoints (start, status, cancel, history)
"""

import os
import io
import uuid
import unittest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

from backend.scraper.crawler import (
    is_ssrf_safe_url,
    normalize_url,
    is_internal_url,
    is_excluded_url,
    extract_internal_links,
    WebsiteCrawler,
)
from backend.scraper.website_scanner import build_website_scan_summary
from backend.website_report_generator import generate_website_pdf_report
from backend.website_history import (
    save_website_scan,
    get_website_scan_by_id,
    get_website_scan_pages,
    get_website_scan_history,
    delete_website_scan,
    register_active_crawler,
    get_active_crawler,
    unregister_active_crawler,
)
from backend.app import (
    WebsiteScanRequest,
    start_website_scan,
    get_website_scan_status,
    get_website_scanned_pages,
    cancel_website_scan,
    get_website_pdf_report,
    get_website_history,
    delete_website_history_item,
    BrowserWebsiteScanStartRequest,
    BrowserWebsitePageSubmission,
    BrowserWebsiteScanFinishRequest,
    start_browser_website_scan,
    submit_browser_website_page,
    finish_browser_website_scan,
    cancel_browser_website_scan_endpoint,
)


class TestSSRFSecurity(unittest.TestCase):
    """Test SSRF protection and hostname resolution boundaries."""

    def test_reject_loopback_and_localhost(self):
        safe, err = is_ssrf_safe_url("http://localhost:8000/page", allow_local=False)
        self.assertFalse(safe)
        self.assertIn("localhost", err.lower())

        safe, err = is_ssrf_safe_url("http://127.0.0.1:5500/", allow_local=False)
        self.assertFalse(safe)
        self.assertIn("localhost/loopback", err.lower())

    def test_reject_cloud_metadata_ip(self):
        safe, err = is_ssrf_safe_url("http://169.254.169.254/latest/meta-data/", allow_local=False)
        self.assertFalse(safe)

    def test_reject_non_http_schemes(self):
        safe, err = is_ssrf_safe_url("ftp://example.com/file.txt", allow_local=False)
        self.assertFalse(safe)
        self.assertIn("invalid scheme", err.lower())

        safe, err = is_ssrf_safe_url("file:///etc/passwd", allow_local=False)
        self.assertFalse(safe)

    def test_allow_local_flag(self):
        safe, err = is_ssrf_safe_url("http://127.0.0.1:5500/test.html", allow_local=True)
        self.assertTrue(safe)
        self.assertIsNone(err)

    def test_reject_empty_or_no_host(self):
        safe, err = is_ssrf_safe_url("http://", allow_local=False)
        self.assertFalse(safe)


class TestURLNormalizationAndFiltering(unittest.TestCase):
    """Test normalization, deduplication, and exclusion filters."""

    def test_normalize_strips_fragments_and_tracking(self):
        url = "https://EXAMPLE.com:443/products/?utm_source=google&utm_medium=cpc&id=123#reviews"
        normalized = normalize_url(url)
        self.assertEqual(normalized, "https://example.com/products?id=123")

    def test_normalize_trailing_slashes(self):
        self.assertEqual(normalize_url("https://example.com/about/"), "https://example.com/about")
        self.assertEqual(normalize_url("https://example.com/"), "https://example.com/")

    def test_is_internal_url(self):
        base = "https://shop.example.com/"
        self.assertTrue(is_internal_url("https://shop.example.com/items", base, allow_subdomains=False))
        self.assertFalse(is_internal_url("https://blog.example.com/items", base, allow_subdomains=False))
        self.assertTrue(is_internal_url("https://blog.example.com/items", base, allow_subdomains=True))
        self.assertFalse(is_internal_url("https://external-phishing.com/items", base, allow_subdomains=True))

    def test_is_excluded_url_static_assets(self):
        self.assertTrue(is_excluded_url("https://example.com/image.png"))
        self.assertTrue(is_excluded_url("https://example.com/doc.pdf"))
        self.assertTrue(is_excluded_url("https://example.com/styles.css"))
        self.assertTrue(is_excluded_url("https://example.com/app.js"))
        self.assertTrue(is_excluded_url("https://example.com/archive.zip"))
        self.assertFalse(is_excluded_url("https://example.com/products/view"))

    def test_is_excluded_url_destructive_paths(self):
        self.assertTrue(is_excluded_url("https://example.com/account/logout"))
        self.assertTrue(is_excluded_url("https://example.com/auth/signout"))
        self.assertTrue(is_excluded_url("https://example.com/user/delete"))
        self.assertFalse(is_excluded_url("https://example.com/user/profile"))

    def test_extract_internal_links(self):
        scraped = {
            "final_url": "https://example.com/store/index",
            "links": [
                {"href": "/store/item1"},
                {"href": "https://example.com/store/item2?utm_source=twitter"},
                {"href": "https://external.com/ads"},
                {"href": "mailto:support@example.com"},
                {"href": "javascript:void(0)"},
                {"href": "/account/logout"},
                {"href": "/assets/banner.jpg"},
            ]
        }
        extracted = extract_internal_links(
            scraped_data=scraped,
            current_url="https://example.com/store/index",
            base_url="https://example.com",
            allow_subdomains=False
        )
        self.assertIn("https://example.com/store/item1", extracted)
        self.assertIn("https://example.com/store/item2", extracted)
        self.assertNotIn("https://external.com/ads", extracted)
        self.assertNotIn("mailto:support@example.com", extracted)
        self.assertNotIn("https://example.com/account/logout", extracted)
        self.assertNotIn("https://example.com/assets/banner.jpg", extracted)


class TestWebsiteCrawlerLimitsAndCancellation(unittest.TestCase):
    """Test crawler queuing, depth limits, and cancellation handling."""

    @patch("backend.scraper.crawler.scrape_website")
    @patch("backend.scraper.crawler.analyze_website")
    def test_crawler_max_pages_limit(self, mock_analyze, mock_scrape):
        mock_scrape.side_effect = lambda url: {
            "scan_status": "complete",
            "url": url,
            "final_url": url,
            "title": f"Page {url}",
            "links": [{"href": f"{url}/subpage1"}, {"href": f"{url}/subpage2"}]
        }
        mock_analyze.return_value = {
            "status": "complete",
            "dark_pattern_analysis": {"risk_score": 10, "risk_level": "Low", "findings": []}
        }

        crawler = WebsiteCrawler(
            base_url="https://example.com",
            max_pages=3,
            max_depth=2,
            allow_local=True,
            page_delay=0.0
        )
        pages = crawler.run()
        self.assertEqual(len(pages), 3)
        self.assertEqual(crawler.status, "completed")

    @patch("backend.scraper.crawler.scrape_website")
    @patch("backend.scraper.crawler.analyze_website")
    def test_crawler_cancellation(self, mock_analyze, mock_scrape):
        def fake_scrape(url):
            # Trigger cancellation during first page
            crawler.cancel()
            return {
                "scan_status": "complete",
                "url": url,
                "final_url": url,
                "title": "Page 1",
                "links": [{"href": "https://example.com/page2"}]
            }

        mock_scrape.side_effect = fake_scrape
        mock_analyze.return_value = {
            "status": "complete",
            "dark_pattern_analysis": {"risk_score": 0, "risk_level": "None", "findings": []}
        }

        crawler = WebsiteCrawler(
            base_url="https://example.com",
            max_pages=10,
            max_depth=2,
            allow_local=True,
            page_delay=0.0
        )
        pages = crawler.run()
        self.assertEqual(len(pages), 1)
        self.assertEqual(crawler.status, "cancelled")
        self.assertTrue(crawler.cancelled)


class TestWebsiteSummaryAggregator(unittest.TestCase):
    """Test website summary calculation, deduplication, and engineering risk score formula."""

    def test_clean_pages_summary(self):
        pages = [
            {"url": "https://example.com/", "title": "Home", "status": "complete", "risk_score": 0, "findings_count": 0, "findings": []},
            {"url": "https://example.com/about", "title": "About", "status": "complete", "risk_score": 0, "findings_count": 0, "findings": []},
        ]
        summary = build_website_scan_summary(
            base_url="https://example.com",
            scan_id="site_scan_001",
            pages_scanned=pages,
            total_discovered=5,
            scan_status="completed",
            duration_seconds=3.2
        )
        self.assertEqual(summary["website_risk_score"], 0)
        self.assertEqual(summary["website_risk_level"], "None")
        self.assertEqual(summary["pages_clean"], 2)
        self.assertEqual(summary["pages_with_dark_patterns"], 0)
        self.assertEqual(summary["coverage_percentage"], 40.0)
        self.assertIn("sample", summary["methodology"].lower())

    def test_deceptive_pages_summary_and_formula(self):
        pages = [
            {
                "url": "https://example.com/sale",
                "title": "Sale",
                "status": "complete",
                "risk_score": 60,
                "findings_count": 1,
                "findings": [{"pattern": "False Urgency", "severity": "High", "evidence": ["Only 2 hours left!"]}]
            },
            {
                "url": "https://example.com/cart",
                "title": "Cart",
                "status": "complete",
                "risk_score": 40,
                "findings_count": 2,
                "findings": [
                    {"pattern": "False Urgency", "severity": "High", "evidence": ["Only 2 hours left!"]},
                    {"pattern": "Hidden Subscription", "severity": "Critical", "evidence": ["Billed monthly"]}
                ]
            },
        ]
        summary = build_website_scan_summary(
            base_url="https://example.com",
            scan_id="site_scan_002",
            pages_scanned=pages,
            total_discovered=2,
            scan_status="completed",
            duration_seconds=5.0
        )
        # Deduplication check: "False Urgency::Only 2 hours left!" occurs on 2 pages but unique findings = 2
        self.assertEqual(summary["total_unique_findings"], 2)
        self.assertEqual(summary["total_finding_occurrences"], 3)
        self.assertEqual(summary["category_counts"]["False Urgency"], 1)
        self.assertEqual(summary["category_counts"]["Hidden Subscription"], 1)

        # Formula check:
        # max_score = 60, avg_score = 50, cat_count = 2 -> cat_score = 40
        # 0.50 * 60 (30) + 0.30 * 50 (15) + 0.20 * 40 (8) = 53
        self.assertEqual(summary["website_risk_score"], 53)
        self.assertEqual(summary["website_risk_level"], "Medium")

    def test_withheld_blocked_pages(self):
        pages = [
            {"url": "https://example.com/blocked", "status": "blocked", "access_blocked": True, "risk_score": None, "findings_count": 0, "findings": []}
        ]
        summary = build_website_scan_summary(
            base_url="https://example.com",
            scan_id="site_scan_003",
            pages_scanned=pages,
            total_discovered=1
        )
        self.assertEqual(summary["pages_blocked"], 1)
        self.assertEqual(summary["risk_distribution"]["withheld"], 1)
        self.assertIsNone(summary["website_risk_score"])
        self.assertEqual(summary["website_risk_level"], "Insufficient Data")
        self.assertTrue(summary["is_partial_scan"])

    def test_insufficient_data_when_all_pages_blocked_or_timed_out(self):
        pages = [
            {"url": "https://example.com/blocked", "status": "blocked", "access_blocked": True, "risk_score": None, "findings_count": 0, "findings": []},
            {"url": "https://example.com/slow", "status": "timed_out", "risk_score": None, "findings_count": 0, "findings": [], "message": "Navigation timed out"}
        ]
        summary = build_website_scan_summary(
            base_url="https://example.com",
            scan_id="site_scan_004",
            pages_scanned=pages,
            total_discovered=5
        )
        self.assertIsNone(summary["website_risk_score"])
        self.assertEqual(summary["website_risk_level"], "Insufficient Data")
        self.assertEqual(summary["pages_blocked"], 1)
        self.assertEqual(summary["pages_timed_out"], 1)
        self.assertEqual(summary["pages_successful"], 0)
        self.assertTrue(summary["is_partial_scan"])
        self.assertIn("insufficient data", summary["methodology"].lower())

    def test_partial_scan_with_timed_out_and_successful_pages(self):
        pages = [
            {
                "url": "https://example.com/deal",
                "title": "Deal",
                "status": "complete",
                "risk_score": 50,
                "findings_count": 1,
                "findings": [{"pattern": "False Urgency", "severity": "Medium", "evidence": ["Hurry!"]}]
            },
            {"url": "https://example.com/slow", "status": "timed_out", "risk_score": None, "findings_count": 0, "findings": []},
            {"url": "https://example.com/err", "status": "failed", "risk_score": None, "findings_count": 0, "findings": []}
        ]
        summary = build_website_scan_summary(
            base_url="https://example.com",
            scan_id="site_scan_005",
            pages_scanned=pages,
            total_discovered=10
        )
        self.assertEqual(summary["pages_successful"], 1)
        self.assertEqual(summary["pages_timed_out"], 1)
        self.assertEqual(summary["pages_failed"], 1)
        self.assertTrue(summary["is_partial_scan"])
        self.assertIsNotNone(summary["website_risk_score"])
        self.assertIn("pages_timed_out", summary)
        self.assertIn("is_partial_scan", summary)


class TestWebsitePDFReportGenerator(unittest.TestCase):
    """Test generating whole website PDF audit reports."""

    def test_generate_website_pdf(self):
        scan_record = {
            "summary": {
                "scan_id": "site_scan_test_123",
                "base_url": "https://shop.example.com",
                "scan_status": "completed",
                "duration_seconds": 14.2,
                "total_pages_discovered": 12,
                "pages_scanned": 8,
                "pages_successful": 7,
                "pages_blocked": 1,
                "pages_clean": 4,
                "pages_with_dark_patterns": 3,
                "coverage_percentage": 66.7,
                "website_risk_score": 58,
                "website_risk_level": "Medium",
                "total_unique_findings": 2,
                "total_finding_occurrences": 4,
                "risk_distribution": {"none": 4, "low": 1, "medium": 2, "high": 0, "very_high": 0, "withheld": 1},
                "highest_risk_pages": [
                    {"url": "https://shop.example.com/deal", "title": "Flash Deal", "depth": 1, "risk_score": 62, "risk_level": "High", "findings_count": 2, "top_patterns": ["False Urgency"]}
                ],
                "unique_findings": [
                    {
                        "pattern": "False Urgency",
                        "severity": "High",
                        "occurrence_count": 3,
                        "evidence": ["Ends in 10 minutes!"],
                        "occurrences": [{"url": "https://shop.example.com/deal", "title": "Flash Deal"}]
                    }
                ],
                "methodology": "Sampling Disclosure: Evaluated 7 sample pages.",
                "config": {"max_pages": 20, "max_depth": 2}
            },
            "pages": [
                {"url": "https://shop.example.com/blocked", "status": "blocked", "access_blocked": True, "block_provider": "Akamai"}
            ]
        }
        pdf_buffer = generate_website_pdf_report(scan_record)
        self.assertIsInstance(pdf_buffer, io.BytesIO)
        content = pdf_buffer.getvalue()
        self.assertTrue(len(content) > 1000)
        self.assertTrue(content.startswith(b"%PDF"))


class TestWebsiteScanAPIEndpoints(unittest.TestCase):
    """Test FastAPI whole website scan endpoints directly."""

    def test_start_website_scan_rejects_invalid_url(self):
        with self.assertRaises(HTTPException) as ctx:
            start_website_scan(WebsiteScanRequest(url="not_a_valid_url"))
        self.assertEqual(ctx.exception.status_code, 400)

    def test_start_website_scan_rejects_ssrf_loopback(self):
        with self.assertRaises(HTTPException) as ctx:
            start_website_scan(WebsiteScanRequest(url="http://127.0.0.1:8000/admin", allow_local=False))
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("URL safety check failed", ctx.exception.detail)

    def test_get_nonexistent_website_scan_returns_404(self):
        with self.assertRaises(HTTPException) as ctx:
            get_website_scan_status("nonexistent_scan_id_999999")
        self.assertEqual(ctx.exception.status_code, 404)

    def test_cancel_nonexistent_website_scan_returns_404(self):
        with self.assertRaises(HTTPException) as ctx:
            cancel_website_scan("nonexistent_scan_id_999999")
        self.assertEqual(ctx.exception.status_code, 404)

    def test_website_history_persistence_lifecycle(self):
        summary = {
            "scan_id": "site_scan_unittest_save_001",
            "base_url": "https://test-example.com",
            "scan_status": "completed",
            "website_risk_score": 35,
            "website_risk_level": "Medium",
            "total_pages_discovered": 4,
            "pages_scanned": 4,
            "pages_successful": 4,
            "pages_blocked": 0,
            "pages_with_dark_patterns": 1,
            "total_unique_findings": 1,
            "duration_seconds": 6.5
        }
        pages = [{"url": "https://test-example.com/", "risk_score": 35}]

        scan_id = save_website_scan(summary, pages)
        self.assertEqual(scan_id, "site_scan_unittest_save_001")

        # Query via status endpoint
        res = get_website_scan_status(scan_id)
        self.assertEqual(res["website_risk_score"], 35)

        # Query pages
        res_pages = get_website_scanned_pages(scan_id)
        self.assertEqual(len(res_pages["pages"]), 1)

        # Query history
        res_hist = get_website_history()
        self.assertTrue(any(item["scan_id"] == scan_id for item in res_hist))

        # PDF download
        res_pdf = get_website_pdf_report(scan_id)
        self.assertEqual(res_pdf.media_type, "application/pdf")
        import asyncio
        async def read_stream():
            chunks = []
            async for c in res_pdf.body_iterator:
                chunks.append(c if isinstance(c, bytes) else c.encode("utf-8"))
            return b"".join(chunks)

        body_bytes = asyncio.run(read_stream())
        self.assertTrue(body_bytes.startswith(b"%PDF"))

        # Delete
        res_del = delete_website_history_item(scan_id)
        self.assertEqual(res_del["status"], "success")

        # Verify gone
        with self.assertRaises(HTTPException) as ctx:
            get_website_scan_status(scan_id)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_website_scan_request_defaults_and_limits(self):
        """Verify default parameters, max_pages bounds (up to 150), and concurrency."""
        req = WebsiteScanRequest(url="https://example.com")
        self.assertEqual(req.max_pages, 20)
        self.assertEqual(req.concurrency, 3)

        with patch("backend.app.WebsiteCrawler") as mock_crawler_cls, \
             patch("backend.app.register_active_crawler"), \
             patch("backend.app.threading.Thread"):
            # Request 120 pages, 4 concurrency
            req2 = WebsiteScanRequest(url="https://example.com", max_pages=120, concurrency=4)
            start_website_scan(req2)
            mock_crawler_cls.assert_called_with(
                base_url="https://example.com",
                scan_id=unittest.mock.ANY,
                max_pages=120,
                max_depth=2,
                concurrency=4,
                allow_subdomains=False,
                allow_local=False
            )

    def test_limit_reached_propagation(self):
        """Verify limit_reached flag is recorded and methodology note mentions crawl cap."""
        summary = build_website_scan_summary(
            base_url="https://example.com",
            scan_id="test_lim_01",
            pages_scanned=[{"url": "https://example.com", "status": "complete", "risk_score": 0, "findings": []}],
            total_discovered=80,
            limit_reached=True,
            config={"max_pages": 50, "concurrency": 3}
        )
        self.assertTrue(summary["limit_reached"])
        self.assertIn("Crawl stopped at configured limit of 50 pages", summary["methodology"])
        self.assertEqual(summary["config"]["concurrency"], 3)


class TestPageSnapshotsAndEvidence(unittest.TestCase):
    """Verifies per-page snapshot storage, traversal protection, finding evidence, and PDF reporting."""

    def setUp(self):
        self.test_scan_id = f"test_snap_scan_{uuid.uuid4().hex[:6]}"
        self.test_page_id = "page_1"
        from PIL import Image as PILImage
        buf = io.BytesIO()
        img = PILImage.new("RGB", (10, 10), color="blue")
        img.save(buf, format="JPEG")
        self.dummy_jpeg = buf.getvalue()

    def tearDown(self):
        delete_website_scan(self.test_scan_id)

    def test_save_and_get_snapshot_path(self):
        """Verify saving snapshot and getting its path safely."""
        from backend.website_history import save_page_snapshot, get_snapshot_path
        saved = save_page_snapshot(self.test_scan_id, self.test_page_id, self.dummy_jpeg)
        self.assertIsNotNone(saved)
        self.assertTrue(os.path.exists(saved))

        retrieved = get_snapshot_path(self.test_scan_id, self.test_page_id)
        self.assertEqual(retrieved, saved)

    def test_path_traversal_prevention(self):
        """Ensure malicious directory traversal identifiers are strictly rejected."""
        from backend.website_history import save_page_snapshot, get_snapshot_path
        self.assertIsNone(save_page_snapshot("../../secret", "page_1", self.dummy_jpeg))
        self.assertIsNone(save_page_snapshot(self.test_scan_id, "../../../etc/passwd", self.dummy_jpeg))
        self.assertIsNone(get_snapshot_path("../../secret", "page_1"))
        self.assertIsNone(get_snapshot_path(self.test_scan_id, "../../../windows/win.ini"))

    def test_crawler_page_and_finding_evidence_enrichment(self):
        """Verify crawler attaches page_id, dom_stats, clean_message, and enriched finding evidence."""
        mock_html = """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <h1>Welcome</h1>
                <p>Hurry! Only 2 items left in stock!</p>
                <button id="buy-btn" class="btn primary">Buy Now</button>
            </body>
        </html>
        """
        mock_scraped = {
            "url": "https://example.com/test",
            "final_url": "https://example.com/test",
            "title": "Test Page",
            "html": mock_html,
            "text": "Welcome Hurry! Only 2 items left in stock! Buy Now",
            "links": [],
            "buttons": [{"text": "Buy Now"}],
            "inputs": [],
            "forms": [],
            "checkboxes": [],
            "dom_elements": [
                {
                    "tag": "p",
                    "text": "Hurry! Only 2 items left in stock!",
                    "selector": "p",
                    "attributes": {},
                    "element_type": "text_block"
                }
            ],
            "cookie_consent": {},
            "headers": {},
            "screenshot_b64": "dummy_b64",
            "scan_status": "complete",
            "navigation_status": "success",
            "access_blocked": False
        }

        with patch("backend.scraper.crawler.scrape_website", return_value=mock_scraped), \
             patch("backend.scraper.crawler.analyze_website") as mock_analyze:
            mock_analyze.return_value = {
                "status": "complete",
                "capture_quality": "complete",
                "access_blocked": False,
                "dark_pattern_analysis": {
                    "risk_score": 45,
                    "risk_level": "Medium",
                    "findings": [
                        {
                            "pattern": "Urgency or Scarcity",
                            "severity": "Medium",
                            "confidence": 0.88,
                            "element_type": "text_block",
                            "evidence": ["only 2 items left"],
                            "description": "Urgency language detected in product copy."
                        }
                    ]
                }
            }

            crawler = WebsiteCrawler(base_url="https://example.com/test", scan_id=self.test_scan_id, max_pages=1)
            pages = crawler.run()

            self.assertEqual(len(pages), 1)
            p0 = pages[0]
            self.assertEqual(p0["page_id"], "page_1")
            self.assertIn("dom_stats", p0)
            self.assertIn("captured_at", p0)
            self.assertTrue(p0["has_screenshot"])
            self.assertEqual(len(p0["findings"]), 1)

            f0 = p0["findings"][0]
            self.assertEqual(f0["page_id"], "page_1")
            self.assertEqual(f0["page_url"], "https://example.com/test")
            self.assertEqual(f0["page_title"], "Test Page")
            self.assertEqual(f0["evidence_type"], "text")
            self.assertEqual(f0["exact_text"], "only 2 items left")
            self.assertEqual(f0["selector"], "p")
            self.assertIn("Urgency", f0["reason"])

    def test_clean_page_audit_status(self):
        """Verify clean pages have clean_message and are not marked blocked."""
        mock_scraped = {
            "url": "https://example.com/clean",
            "final_url": "https://example.com/clean",
            "title": "Clean Page",
            "html": "<html><body><h1>Transparent Website</h1></body></html>",
            "text": "Transparent Website",
            "links": [],
            "buttons": [],
            "inputs": [],
            "scan_status": "complete",
            "access_blocked": False
        }

        with patch("backend.scraper.crawler.scrape_website", return_value=mock_scraped), \
             patch("backend.scraper.crawler.analyze_website") as mock_analyze:
            mock_analyze.return_value = {
                "status": "complete",
                "capture_quality": "complete",
                "access_blocked": False,
                "dark_pattern_analysis": {
                    "risk_score": 0,
                    "risk_level": "None",
                    "findings": []
                }
            }

            crawler = WebsiteCrawler(base_url="https://example.com", scan_id=self.test_scan_id, max_pages=1)
            pages = crawler.run()
            self.assertEqual(len(pages), 1)
            self.assertEqual(pages[0]["findings_count"], 0)
            self.assertEqual(pages[0]["clean_message"], "No dark patterns detected on this captured page.")

    def test_website_pdf_report_with_page_snapshots(self):
        """Verify PDF report generator generates valid PDF with page audit section and embedded snapshots."""
        from backend.website_report_generator import generate_website_pdf_report
        from backend.website_history import save_page_snapshot

        save_page_snapshot(self.test_scan_id, "page_1", self.dummy_jpeg)

        mock_record = {
            "summary": {
                "scan_id": self.test_scan_id,
                "base_url": "https://example.com",
                "scan_status": "completed",
                "website_risk_score": 35,
                "website_risk_level": "Medium",
                "pages_scanned": 1,
                "pages_successful": 1,
                "pages_clean": 0,
                "pages_blocked": 0,
                "pages_with_dark_patterns": 1,
                "total_unique_findings": 1,
                "duration_seconds": 1.2,
                "category_counts": {"Urgency": 1},
                "unique_findings": [
                    {
                        "pattern": "Urgency",
                        "severity": "Medium",
                        "occurrence_count": 1,
                        "evidence": ["only 1 left"],
                        "occurrences": [{"url": "https://example.com"}]
                    }
                ]
            },
            "pages": [
                {
                    "page_id": "page_1",
                    "url": "https://example.com",
                    "title": "Example Domain",
                    "status": "complete",
                    "risk_score": 35,
                    "risk_level": "Medium",
                    "findings_count": 1,
                    "findings": [
                        {
                            "pattern": "Urgency",
                            "severity": "Medium",
                            "confidence": 0.92,
                            "evidence_type": "text",
                            "exact_text": "only 1 left",
                            "selector": "p.urgency",
                            "reason": "AI model detected urgency pattern"
                        }
                    ]
                }
            ]
        }

        pdf_buffer = generate_website_pdf_report(mock_record)
        self.assertIsNotNone(pdf_buffer)
        pdf_bytes = pdf_buffer.getvalue()
        self.assertTrue(len(pdf_bytes) > 1000)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))


class TestBrowserWebsiteScanEndpoints(unittest.TestCase):
    """Test browser-driven whole website scan API workflow."""

    def setUp(self):
        self.created_scans = []

    def tearDown(self):
        for sid in self.created_scans:
            try:
                delete_website_scan(sid)
            except Exception:
                pass

    def test_start_browser_website_scan_rejects_ssrf(self):
        """Verify start rejects SSRF URLs unless allow_local is set."""
        req = BrowserWebsiteScanStartRequest(url="http://127.0.0.1:8000/page", allow_local=False)
        with self.assertRaises(HTTPException) as cm:
            start_browser_website_scan(req)
        self.assertEqual(cm.exception.status_code, 400)
        self.assertIn("safety check failed", cm.exception.detail)

    def test_start_browser_website_scan_success(self):
        """Verify starting a browser website scan returns session and scan_id."""
        req = BrowserWebsiteScanStartRequest(url="https://example.com", max_pages=15, max_depth=2)
        res = start_browser_website_scan(req)
        self.assertIn("scan_id", res)
        self.assertEqual(res["status"], "crawling")
        self.assertEqual(res["base_url"], "https://example.com/")
        self.created_scans.append(res["scan_id"])

    def test_submit_page_and_finish_flow(self):
        """Verify full lifecycle: start -> submit pages -> check status -> finish."""
        start_res = start_browser_website_scan(
            BrowserWebsiteScanStartRequest(url="https://example.com", max_pages=10)
        )
        scan_id = start_res["scan_id"]
        self.created_scans.append(scan_id)

        # Submit page 1 (clean page)
        page1 = BrowserWebsitePageSubmission(
            url="https://example.com",
            title="Example Domain",
            depth=0,
            html="<html><head><title>Example</title></head><body><h1>Welcome</h1><p>Normal transparent text</p></body></html>",
            text="Welcome Normal transparent text",
            elements=[{"element_type": "heading", "tag": "h1", "text": "Welcome"}]
        )
        sub1_res = submit_browser_website_page(scan_id, page1)
        self.assertEqual(sub1_res["status"], "success")
        self.assertEqual(sub1_res["page_id"], "page_1")
        self.assertEqual(sub1_res["page_record"]["findings_count"], 0)

        # Check live status via existing get_website_scan_status
        status_res = get_website_scan_status(scan_id)
        self.assertEqual(status_res["scan_id"], scan_id)
        self.assertEqual(status_res["pages_scanned"], 1)

        # Submit page 2 (with urgency deceptive pattern)
        page2 = BrowserWebsitePageSubmission(
            url="https://example.com/checkout",
            title="Checkout",
            depth=1,
            html="<html><body><p class='hurry'>Hurry! Only 2 items left in stock at this price!</p></body></html>",
            text="Hurry! Only 2 items left in stock at this price!",
            elements=[{"element_type": "text_block", "tag": "p", "text": "Hurry! Only 2 items left in stock at this price!"}]
        )
        sub2_res = submit_browser_website_page(scan_id, page2)
        self.assertEqual(sub2_res["status"], "success")
        self.assertEqual(sub2_res["page_id"], "page_2")
        self.assertGreaterEqual(sub2_res["page_record"]["findings_count"], 1)

        # Check pages endpoint
        pages_res = get_website_scanned_pages(scan_id)
        self.assertEqual(len(pages_res["pages"]), 2)

        # Finish scan
        finish_res = finish_browser_website_scan(scan_id, BrowserWebsiteScanFinishRequest(total_discovered=5))
        self.assertIn("summary", finish_res)
        summary = finish_res["summary"]
        self.assertEqual(summary["scan_id"], scan_id)
        self.assertEqual(summary["scan_status"], "completed")
        self.assertEqual(summary["pages_scanned"], 2)
        self.assertGreater(summary["website_risk_score"], 0)

    def test_cancel_browser_scan(self):
        """Verify cancelling a browser scan stops cleanly and saves summary."""
        start_res = start_browser_website_scan(BrowserWebsiteScanStartRequest(url="https://example.com/test-cancel"))
        scan_id = start_res["scan_id"]
        self.created_scans.append(scan_id)

        cancel_res = cancel_browser_website_scan_endpoint(scan_id)
        self.assertEqual(cancel_res["status"], "cancelled")
        self.assertEqual(cancel_res["summary"]["scan_status"], "cancelled")


if __name__ == "__main__":
    unittest.main()



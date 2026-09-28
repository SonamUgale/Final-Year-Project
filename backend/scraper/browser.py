import base64
import logging
import os
import time
from urllib.parse import urlparse

from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
    Error as PlaywrightError,
)

logger = logging.getLogger("darkshield.scraper")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def find_edge_executable():
    """
    Find Microsoft Edge installed on Windows.
    Preserves exact existing path discovery order.
    """
    possible_paths = [
        os.path.expandvars(
            r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
        ),
        os.path.expandvars(
            r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
        ),
        os.path.expandvars(
            r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"
        ),
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return path

    return None


def _classify_playwright_error(err_str: str) -> tuple[str, str]:
    """Classify Playwright / network error into error_type and clean message."""
    lower_err = err_str.lower()
    if "err_name_not_resolved" in lower_err or "getaddrinfo" in lower_err:
        return "dns_failure", "Domain name could not be resolved (DNS failure). Please verify the URL."
    elif "err_connection_refused" in lower_err:
        return "connection_refused", "Connection refused by the host server. Ensure the port and host are active."
    elif "err_connection_reset" in lower_err:
        return "connection_reset", "The connection was abruptly reset by the remote server."
    elif "err_connection_closed" in lower_err:
        return "connection_closed", "The connection was closed before completing transmission."
    elif "err_network_changed" in lower_err:
        return "network_changed", "Local network connection changed during navigation."
    elif "err_cert" in lower_err or "err_ssl" in lower_err:
        return "ssl_error", "SSL/TLS certificate error or handshake failure."
    elif "timeout" in lower_err:
        return "navigation_timeout", "The website did not respond within the navigation timeout."
    return "navigation_error", f"Network or navigation error: {err_str[:120]}"


def _detect_bot_or_blocked(title: str, text: str, status_code: int = 200) -> bool:
    """Detect whether the page has an anti-bot challenge or block wall."""
    if status_code in [403, 429]:
        return True
    
    t_lower = (title or "").lower()
    text_snippet = (text or "")[:1500].lower()

    bot_phrases = [
        "robot check",
        "attention required! | cloudflare",
        "just a moment...",
        "cf-turnstile",
        "checking your browser before accessing",
        "please verify you are a human",
        "access denied",
        "pardon our interruption",
        "security check",
        "complete captcha",
        "enter the characters you see below",
    ]

    for phrase in bot_phrases:
        if phrase in t_lower or phrase in text_snippet:
            return True

    return False


def scrape_website(url: str) -> dict:
    """
    Resilient, fault-tolerant website scraper powered by Playwright + Microsoft Edge.
    
    Handles:
    - Normal successful navigation (scan_status: complete, navigation_status: success)
    - Slow / dynamic page navigation timeouts with partial content recovery (scan_status: partial, navigation_status: timeout)
    - Anti-bot / CAPTCHA challenge pages (scan_status: blocked_or_interaction_required)
    - Network errors with 1 bounded retry (scan_status: failed, navigation_status: failed)
    - URL redirects (preserves requested_url and final_url)
    - Independent fault-tolerant extraction of text, links, buttons, inputs, DOM candidates, screenshot, and cookie banners
    """
    t0 = time.time()
    logger.info(f"Initiating scan for requested URL: {url}")

    edge_path = find_edge_executable()
    if not edge_path:
        logger.error("Microsoft Edge was not found on this system.")
        return {
            "scan_status": "failed",
            "navigation_status": "failed",
            "requested_url": url,
            "final_url": url,
            "url": url,
            "title": "Browser Missing",
            "text": "",
            "links": [],
            "buttons": [],
            "inputs": [],
            "headers": {},
            "dom_elements": [],
            "screenshot_b64": None,
            "cookie_consent": {},
            "scan_duration_seconds": round(time.time() - t0, 2),
            "warning": None,
            "error_type": "edge_not_found",
            "message": "Microsoft Edge executable was not found. Please install Microsoft Edge.",
        }

    # State variables
    navigation_status = "success"
    scan_status = "complete"
    warning_msg = None
    error_type = None
    error_message = None
    final_url = url
    headers = {}
    response = None

    with sync_playwright() as p:
        browser = None
        context = None
        page = None

        try:
            browser = p.chromium.launch(
                executable_path=edge_path,
                headless=True,
                args=[
                    "--disable-gpu",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-background-networking",
                    "--disable-features=Translate,OptimizationHints,MediaRouter",
                ],
            )

            context = browser.new_context(
                viewport={"width": 1440, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
                ignore_https_errors=True,
            )

            page = context.new_page()

            # -------------------------------------------------
            # RESILIENT NAVIGATION WITH BOUNDED RETRY
            # -------------------------------------------------
            nav_timeout = 20000  # 20 seconds navigation timeout
            nav_attempts = 0
            max_nav_attempts = 2  # At most 1 initial + 1 retry

            while nav_attempts < max_nav_attempts:
                nav_attempts += 1
                try:
                    logger.info(f"Navigating to {url} (attempt {nav_attempts}/{max_nav_attempts}, timeout {nav_timeout}ms)...")
                    response = page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=nav_timeout,
                    )
                    # Navigation succeeded normally
                    navigation_status = "success"
                    scan_status = "complete"
                    break

                except PlaywrightTimeoutError as te:
                    logger.warning(f"Navigation timeout exceeded ({nav_timeout}ms) for {url}.")
                    # Check whether document has partially loaded
                    body_len = 0
                    try:
                        body_len = page.evaluate("() => (document.body && document.body.innerText) ? document.body.innerText.trim().length : 0")
                    except Exception:
                        body_len = 0

                    if body_len > 0:
                        # Page is usable despite timeout!
                        logger.info(f"Recovered partial DOM content ({body_len} chars) from timed-out page.")
                        navigation_status = "timeout"
                        scan_status = "partial"
                        warning_msg = (
                            "The page did not finish loading within the navigation timeout, "
                            "but available content was analyzed."
                        )
                        break
                    else:
                        # Completely empty on timeout
                        if nav_attempts < max_nav_attempts:
                            logger.info(f"Page was blank after timeout. Retrying once with commit...")
                            time.sleep(1.0)
                            try:
                                response = page.goto(url, wait_until="commit", timeout=12000)
                                navigation_status = "timeout"
                                scan_status = "partial"
                                warning_msg = "The page took long to load; partial structure was analyzed."
                                break
                            except Exception:
                                pass
                        
                        navigation_status = "timeout"
                        scan_status = "failed"
                        error_type = "navigation_timeout"
                        error_message = "The website did not load within timeout and no usable content could be retrieved."
                        break

                except PlaywrightError as pe:
                    err_str = str(pe)
                    logger.warning(f"Playwright navigation error on attempt {nav_attempts}: {err_str}")
                    etype, emsg = _classify_playwright_error(err_str)
                    
                    # Retryable transient network errors
                    if nav_attempts < max_nav_attempts and etype in ["network_changed", "connection_reset", "connection_closed"]:
                        logger.info(f"Encountered transient error '{etype}'. Retrying once after 1s delay...")
                        time.sleep(1.0)
                        continue

                    # Non-retryable or retries exhausted
                    # Check if page has content despite the error
                    body_len = 0
                    try:
                        body_len = page.evaluate("() => (document.body && document.body.innerText) ? document.body.innerText.trim().length : 0")
                    except Exception:
                        body_len = 0

                    if body_len > 0:
                        navigation_status = "timeout"
                        scan_status = "partial"
                        warning_msg = f"Network warning during load ({etype}), but available page content was retrieved."
                        break
                    else:
                        navigation_status = "failed"
                        scan_status = "failed"
                        error_type = etype
                        error_message = emsg
                        break

            # Record final URL after navigation & redirects
            try:
                final_url = page.url or url
            except Exception:
                final_url = url

            if final_url != url:
                logger.info(f"Website redirect detected: {url} -> {final_url}")

            # If scan totally failed and no content exists, return structured failed response
            if scan_status == "failed":
                logger.warning(f"Scan marked as failed for {url}: {error_type} - {error_message}")
                return {
                    "scan_status": "failed",
                    "navigation_status": navigation_status,
                    "requested_url": url,
                    "final_url": final_url,
                    "url": final_url or url,
                    "title": "Website Unavailable",
                    "text": "",
                    "links": [],
                    "buttons": [],
                    "inputs": [],
                    "headers": {},
                    "dom_elements": [],
                    "screenshot_b64": None,
                    "cookie_consent": {},
                    "scan_duration_seconds": round(time.time() - t0, 2),
                    "warning": None,
                    "error_type": error_type or "navigation_error",
                    "message": error_message or "Unable to load the website for analysis.",
                }

            # If page succeeded or is partial, give JS a brief moment to stabilize
            if scan_status == "complete":
                try:
                    page.wait_for_timeout(1000)
                except Exception:
                    pass

            # -------------------------------------------------
            # HTTP RESPONSE HEADERS
            # -------------------------------------------------
            http_status = 200
            if response:
                try:
                    headers = response.all_headers() or {}
                    http_status = response.status
                except Exception:
                    headers = {}
                    http_status = 200

            # -------------------------------------------------
            # PAGE TITLE EXTRACTION (Fault-Tolerant)
            # -------------------------------------------------
            title = ""
            try:
                title = page.title() or ""
            except Exception:
                title = ""

            # -------------------------------------------------
            # BODY TEXT EXTRACTION (Fault-Tolerant)
            # -------------------------------------------------
            text = ""
            try:
                text = page.evaluate("() => document.body ? (document.body.innerText || '') : ''") or ""
            except Exception:
                text = ""

            # -------------------------------------------------
            # ANTI-BOT / BLOCKED SITE DETECTION
            # -------------------------------------------------
            is_blocked = _detect_bot_or_blocked(title, text, http_status)
            if is_blocked:
                logger.warning(f"Bot protection or access challenge detected for {final_url} (HTTP {http_status})")
                scan_status = "blocked_or_interaction_required"
                navigation_status = "blocked_or_interaction_required"
                warning_msg = (
                    "This website presented an anti-bot challenge or requires human interaction "
                    "(e.g., CAPTCHA, Cloudflare, or Access Verification). "
                    "Automated analysis was restricted to accessible content."
                )

            # -------------------------------------------------
            # VISUAL SCREENSHOT (Fault-Tolerant)
            # -------------------------------------------------
            screenshot_b64 = None
            try:
                screenshot_bytes = page.screenshot(
                    type="jpeg",
                    quality=75,
                    full_page=False,
                    timeout=5000,
                )
                screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
                logger.info(f"Visual snapshot captured ({len(screenshot_b64)} chars base64)")
            except Exception as ss_err:
                logger.debug(f"Screenshot capture skipped or failed: {ss_err}")
                screenshot_b64 = None

            # -------------------------------------------------
            # INTERACTIVE ELEMENTS: LINKS, BUTTONS, INPUTS (Single-Shot JS Evaluate)
            # -------------------------------------------------
            links = []
            buttons = []
            inputs = []

            try:
                extracted_elements = page.evaluate("""
                    () => {
                        const links = [];
                        const buttons = [];
                        const inputs = [];

                        // 1. Links
                        document.querySelectorAll('a').forEach((a, idx) => {
                            if (idx >= 200) return;
                            const txt = (a.innerText || a.textContent || '').trim();
                            const href = a.getAttribute('href');
                            if (txt || href) {
                                links.push({ text: txt.slice(0, 150), href: href });
                            }
                        });

                        // 2. Buttons
                        document.querySelectorAll('button, [role="button"], input[type="button"], input[type="submit"]').forEach((b, idx) => {
                            if (idx >= 150) return;
                            const txt = (b.innerText || b.value || b.getAttribute('aria-label') || '').trim();
                            if (txt) {
                                buttons.push({ text: txt.slice(0, 120) });
                            }
                        });

                        // 3. Inputs
                        document.querySelectorAll('input, textarea, select').forEach((i, idx) => {
                            if (idx >= 80) return;
                            inputs.push({
                                type: i.getAttribute('type') || i.tagName.toLowerCase(),
                                name: i.getAttribute('name') || null,
                                placeholder: i.getAttribute('placeholder') || null
                            });
                        });

                        return { links, buttons, inputs };
                    }
                """)
                links = extracted_elements.get("links", [])
                buttons = extracted_elements.get("buttons", [])
                inputs = extracted_elements.get("inputs", [])
            except Exception as elem_err:
                logger.warning(f"Batch element extraction fallback triggered: {elem_err}")
                links, buttons, inputs = [], [], []

            # -------------------------------------------------
            # COOKIE CONSENT BANNER DETECTION (Fault-Tolerant)
            # -------------------------------------------------
            cookie_consent = {
                "banner_detected": False,
                "banner_text": "",
                "accept_button": None,
                "reject_button": None,
                "manage_button": None,
                "preselected_checkboxes": [],
                "has_close_button": False,
            }
            try:
                cookie_consent = page.evaluate(r"""
                    () => {
                        const data = {
                            banner_detected: false,
                            banner_text: "",
                            accept_button: null,
                            reject_button: null,
                            manage_button: null,
                            preselected_checkboxes: [],
                            has_close_button: false
                        };

                        function isVisible(el) {
                            if (!el) return false;
                            const style = window.getComputedStyle(el);
                            return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
                        }

                        const selectors = [
                            '#onetrust-banner-sdk',
                            '#cookie-banner',
                            '.cookie-banner',
                            '#cookie-consent',
                            '.cookie-consent',
                            '#cookie-notice',
                            '.cookie-notice',
                            '#cookieConsent',
                            '.cookieConsent',
                            '#cookies-banner',
                            '.cookies-banner',
                            '.cc-banner',
                            'div[aria-label*="cookie" i]',
                            'div[aria-label*="consent" i]',
                            'div[id*="consent" i]',
                            'div[class*="consent" i]'
                        ];

                        let bannerEl = null;
                        for (const sel of selectors) {
                            const found = document.querySelector(sel);
                            if (found && isVisible(found)) {
                                bannerEl = found;
                                break;
                            }
                        }

                        if (!bannerEl) {
                            const allDivs = document.querySelectorAll('div, section, footer');
                            for (let i = 0; i < Math.min(allDivs.length, 60); i++) {
                                const d = allDivs[i];
                                const txt = (d.innerText || '').toLowerCase();
                                if ((txt.includes('we use cookies') || txt.includes('accept all cookies') || txt.includes('cookie settings')) && isVisible(d) && d.innerText.length < 1000) {
                                    bannerEl = d;
                                    break;
                                }
                            }
                        }

                        if (bannerEl) {
                            data.banner_detected = true;
                            data.banner_text = (bannerEl.innerText || '').slice(0, 400);

                            const btns = bannerEl.querySelectorAll('button, a, input[type="button"], input[type="submit"]');
                            btns.forEach(b => {
                                const bText = (b.innerText || b.value || '').trim();
                                const lower = bText.toLowerCase();
                                if (!data.accept_button && (lower.includes('accept all') || lower.includes('agree') || lower.includes('allow all') || lower === 'accept' || lower === 'i agree' || lower === 'ok')) {
                                    data.accept_button = bText;
                                } else if (!data.reject_button && (lower.includes('reject all') || lower.includes('decline') || lower.includes('disagree') || lower === 'reject' || lower === 'refuse')) {
                                    data.reject_button = bText;
                                } else if (!data.manage_button && (lower.includes('manage') || lower.includes('settings') || lower.includes('preferences') || lower.includes('customize'))) {
                                    data.manage_button = bText;
                                }
                            });

                            const checkboxes = bannerEl.querySelectorAll('input[type="checkbox"]');
                            checkboxes.forEach(cb => {
                                if (cb.checked) {
                                    const label = cb.closest('label') || document.querySelector(`label[for="${cb.id}"]`);
                                    const labelText = label ? label.innerText.trim() : (cb.name || cb.id || 'Tracking');
                                    const isEssential = /necessary|essential|strictly/i.test(labelText);
                                    data.preselected_checkboxes.push({
                                        name: cb.name || cb.id || 'checkbox',
                                        label: labelText,
                                        is_essential: isEssential,
                                        disabled: cb.disabled
                                    });
                                }
                            });

                            const closeBtn = bannerEl.querySelector('[aria-label*="close" i], .close, .dismiss, button[title*="close" i]');
                            if (closeBtn) {
                                data.has_close_button = true;
                            }
                        }

                        return data;
                    }
                """)
            except Exception as c_err:
                logger.debug(f"Cookie consent parsing exception: {c_err}")

            # -------------------------------------------------
            # STRUCTURED DOM CANDIDATE EXTRACTION (Fault-Tolerant)
            # -------------------------------------------------
            dom_elements = []
            try:
                dom_elements = page.evaluate("""
                    () => {
                        const candidates = [];
                        const seen = new Set();

                        function addCandidate(el, type) {
                            if (!el || candidates.length >= 120) return;
                            const text = (el.innerText || el.textContent || '').trim();
                            if (!text || text.length < 3 || text.length > 500) return;

                            let context = '';
                            if (el.parentElement) {
                                const pText = (el.parentElement.innerText || '').trim();
                                if (pText && pText !== text) {
                                    context = pText.slice(0, 250);
                                }
                            }

                            const key = type + ':' + text;
                            if (!seen.has(key)) {
                                seen.add(key);
                                candidates.push({
                                    element_type: type,
                                    tag: el.tagName ? el.tagName.toLowerCase() : '',
                                    text: text,
                                    context: context
                                });
                            }
                        }

                        // Headings
                        document.querySelectorAll('h1, h2, h3, h4, h5, h6').forEach(el => addCandidate(el, 'heading'));

                        // Buttons & CTA triggers
                        document.querySelectorAll('button, [role="button"], input[type="button"], input[type="submit"], a.btn, a.button').forEach(el => addCandidate(el, 'button'));

                        // Actionable Links
                        document.querySelectorAll('a').forEach(el => {
                            const txt = (el.innerText || '').trim();
                            if (txt && txt.length >= 3 && txt.length <= 150) {
                                addCandidate(el, 'link');
                            }
                        });

                        // Labels
                        document.querySelectorAll('label').forEach(el => addCandidate(el, 'label'));

                        // Input placeholders
                        document.querySelectorAll('input[placeholder], textarea[placeholder]').forEach(el => {
                            const ph = el.getAttribute('placeholder');
                            if (ph && ph.trim().length >= 3) {
                                const key = 'input_placeholder:' + ph.trim();
                                if (!seen.has(key)) {
                                    seen.add(key);
                                    candidates.push({
                                        element_type: 'input_placeholder',
                                        tag: el.tagName ? el.tagName.toLowerCase() : '',
                                        text: ph.trim(),
                                        context: el.name ? `Input field name: ${el.name}` : ''
                                    });
                                }
                            }
                        });

                        // Banners, modals, alerts, notices, timers
                        document.querySelectorAll('[role="alert"], [role="dialog"], .banner, .alert, .notice, .countdown, .timer, .modal, .toast, .badge, .popup').forEach(el => addCandidate(el, 'banner_or_dialog'));

                        // Text blocks & paragraphs
                        document.querySelectorAll('p, strong, b, em, span').forEach(el => {
                            const txt = (el.innerText || '').trim();
                            if (txt.length >= 8 && txt.length <= 300 && el.children.length <= 1) {
                                addCandidate(el, 'text_block');
                            }
                        });

                        return candidates;
                    }
                """)
            except Exception as dom_err:
                logger.warning(f"DOM candidate evaluation error: {dom_err}")
                dom_elements = []

            duration = round(time.time() - t0, 2)
            logger.info(
                f"Scraping completed for {final_url} in {duration}s — "
                f"Status: {scan_status} ({navigation_status}), "
                f"Text: {len(text)} chars, Links: {len(links)}, Buttons: {len(buttons)}, Inputs: {len(inputs)}"
            )

            return {
                "scan_status": scan_status,
                "navigation_status": navigation_status,
                "requested_url": url,
                "final_url": final_url,
                "url": final_url or url,
                "title": title or "Untitled Website",
                "text": text,
                "links": links,
                "buttons": buttons,
                "inputs": inputs,
                "headers": headers,
                "dom_elements": dom_elements or [],
                "screenshot_b64": screenshot_b64,
                "cookie_consent": cookie_consent,
                "scan_duration_seconds": duration,
                "warning": warning_msg,
                "error_type": error_type,
                "message": error_message,
            }

        except Exception as error:
            logger.exception(f"Unexpected scraping error for {url}: {error}")
            duration = round(time.time() - t0, 2)
            etype, emsg = _classify_playwright_error(str(error))
            return {
                "scan_status": "failed",
                "navigation_status": "failed",
                "requested_url": url,
                "final_url": final_url or url,
                "url": final_url or url,
                "title": "Scan Failed",
                "text": "",
                "links": [],
                "buttons": [],
                "inputs": [],
                "headers": {},
                "dom_elements": [],
                "screenshot_b64": None,
                "cookie_consent": {},
                "scan_duration_seconds": duration,
                "warning": None,
                "error_type": etype,
                "message": emsg or f"Unable to scan the website: {str(error)}",
            }

        finally:
            if context:
                try:
                    context.close()
                except Exception:
                    pass
            if browser:
                try:
                    browser.close()
                except Exception:
                    pass
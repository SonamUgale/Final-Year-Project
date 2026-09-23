import base64
import os
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright


def find_edge_executable():
    """
    Find Microsoft Edge installed on Windows.
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


def scrape_website(url: str):

    edge_path = find_edge_executable()

    if not edge_path:
        raise RuntimeError(
            "Microsoft Edge was not found on this computer. "
            "Please install Microsoft Edge."
        )

    with sync_playwright() as p:

        browser = None

        try:
            # Use the actual Microsoft Edge installed on the computer.
            browser = p.chromium.launch(
                executable_path=edge_path,
                headless=True,
                args=[
                    "--disable-gpu",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )

            page = browser.new_page(
                viewport={
                    "width": 1440,
                    "height": 900,
                },
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
            )

            # Load the website.
            response = page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=30000,
            )

            # Give JavaScript-based websites a short time to render.
            try:
                page.wait_for_load_state(
                    "networkidle",
                    timeout=10000,
                )
            except Exception:
                # Some websites never reach networkidle.
                pass

            # HTTP response headers.
            headers = {}

            if response:
                try:
                    headers = response.all_headers()
                except Exception:
                    headers = {}

            # Capture visual screenshot of the website (JPEG for efficient payload size)
            screenshot_b64 = None
            try:
                screenshot_bytes = page.screenshot(
                    type="jpeg",
                    quality=75,
                    full_page=False,
                    timeout=8000
                )
                screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
            except Exception:
                screenshot_b64 = None

            # Detect cookie consent banners and privacy preference structures
            cookie_consent = {
                "banner_detected": False,
                "banner_text": "",
                "accept_button": None,
                "reject_button": None,
                "manage_button": None,
                "preselected_checkboxes": [],
                "has_close_button": False
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
                            '#qc-cmp2-container',
                            '[aria-label*="cookie" i]',
                            '[aria-label*="consent" i]',
                            '[class*="cookie-banner" i]',
                            '[class*="cookie_banner" i]',
                            '[class*="cookie-consent" i]',
                            '[id*="cookie-consent" i]',
                            '[id*="cookie-banner" i]'
                        ];

                        let bannerEl = null;
                        for (const sel of selectors) {
                            const el = document.querySelector(sel);
                            if (el && isVisible(el)) {
                                bannerEl = el;
                                break;
                            }
                        }

                        if (!bannerEl) {
                            const fixedElements = document.querySelectorAll('[role="dialog"], [role="alertdialog"], div');
                            for (const el of fixedElements) {
                                const style = window.getComputedStyle(el);
                                if ((style.position === 'fixed' || style.position === 'sticky') && isVisible(el)) {
                                    const txt = (el.innerText || '').toLowerCase();
                                    if ((txt.includes('cookie') || txt.includes('privacy preferences')) && txt.length > 20 && txt.length < 1500) {
                                        bannerEl = el;
                                        break;
                                    }
                                }
                            }
                        }

                        if (bannerEl) {
                            data.banner_detected = true;
                            data.banner_text = (bannerEl.innerText || '').slice(0, 500).trim();

                            const buttons = bannerEl.querySelectorAll('button, a[role="button"], input[type="button"], a.btn, a.button');
                            buttons.forEach(btn => {
                                const bText = (btn.innerText || btn.value || '').trim();
                                const lower = bText.toLowerCase();
                                if (!lower) return;

                                if (/accept(\s+all)?|allow(\s+all)?|agree|i\s+understand|got\s+it|ok/i.test(lower)) {
                                    if (!data.accept_button) data.accept_button = bText;
                                } else if (/reject(\s+all)?|decline(\s+all)?|refuse|disagree|only\s+essential|necessary\s+only/i.test(lower)) {
                                    if (!data.reject_button) data.reject_button = bText;
                                } else if (/manage|settings|preferences|customize|options/i.test(lower)) {
                                    if (!data.manage_button) data.manage_button = bText;
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
            except Exception:
                pass

            # Basic website information.
            result = {
                "url": url,
                "title": page.title(),
                "text": "",
                "links": [],
                "buttons": [],
                "inputs": [],
                "headers": headers,
                "screenshot_b64": screenshot_b64,
                "cookie_consent": cookie_consent,
            }

            # Extract page text.
            try:
                result["text"] = page.locator("body").inner_text(
                    timeout=10000
                )
            except Exception:
                result["text"] = ""

            # Extract links.
            try:
                links = page.locator("a").all()

                for link in links:
                    try:
                        text = link.inner_text().strip()
                    except Exception:
                        text = ""

                    try:
                        href = link.get_attribute("href")
                    except Exception:
                        href = None

                    result["links"].append(
                        {
                            "text": text,
                            "href": href,
                        }
                    )

            except Exception:
                pass

            # Extract buttons.
            try:
                buttons = page.locator("button").all()

                for button in buttons:
                    try:
                        button_text = button.inner_text().strip()
                    except Exception:
                        button_text = ""

                    result["buttons"].append(
                        {
                            "text": button_text,
                        }
                    )

            except Exception:
                pass

            # Extract input fields.
            try:
                inputs = page.locator("input").all()

                for input_field in inputs:

                    try:
                        input_type = input_field.get_attribute("type")
                    except Exception:
                        input_type = None

                    try:
                        input_name = input_field.get_attribute("name")
                    except Exception:
                        input_name = None

                    try:
                        placeholder = input_field.get_attribute(
                            "placeholder"
                        )
                    except Exception:
                        placeholder = None

                    result["inputs"].append(
                        {
                            "type": input_type,
                            "name": input_name,
                            "placeholder": placeholder,
                        }
                    )

            except Exception:
                pass

            # Extract structured DOM candidate elements with surrounding context
            try:
                dom_elements = page.evaluate("""
                    () => {
                        const candidates = [];
                        const seen = new Set();

                        function addCandidate(el, type) {
                            if (!el) return;
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
                result["dom_elements"] = dom_elements or []
            except Exception as dom_err:
                result["dom_elements"] = []

            return result

        except Exception as error:

            raise RuntimeError(
                f"Unable to scan the website: {str(error)}"
            ) from error

        finally:

            if browser:
                try:
                    browser.close()
                except Exception:
                    pass
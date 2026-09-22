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

            # Basic website information.
            result = {
                "url": url,
                "title": page.title(),
                "text": "",
                "links": [],
                "buttons": [],
                "inputs": [],
                "headers": headers,
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
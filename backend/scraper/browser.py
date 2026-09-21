from playwright.sync_api import sync_playwright


def scrape_website(url: str):

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=True)

        page = browser.new_page()

        # Open the website and capture the main HTTP response
        response = page.goto(
            url,
            wait_until="networkidle",
            timeout=30000
        )

        # Extract HTTP response headers
        headers = {}

        if response:
            headers = response.all_headers()

        # Basic website information
        result = {
            "url": url,
            "title": page.title(),
            "text": page.locator("body").inner_text(),

            "links": [],

            "buttons": [],

            "inputs": [],

            "headers": headers
        }

        # -----------------------------------------
        # Extract links
        # -----------------------------------------

        links = page.locator("a").all()

        for link in links:

            text = link.inner_text().strip()
            href = link.get_attribute("href")

            result["links"].append({
                "text": text,
                "href": href
            })

        # -----------------------------------------
        # Extract buttons
        # -----------------------------------------

        buttons = page.locator("button").all()

        for button in buttons:

            result["buttons"].append({
                "text": button.inner_text().strip()
            })

        # -----------------------------------------
        # Extract input fields
        # -----------------------------------------

        inputs = page.locator("input").all()

        for input_field in inputs:

            result["inputs"].append({
                "type": input_field.get_attribute("type"),
                "name": input_field.get_attribute("name"),
                "placeholder": input_field.get_attribute("placeholder")
            })

        # Close browser
        browser.close()

        return result
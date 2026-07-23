import argparse

from playwright.sync_api import sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


parser = argparse.ArgumentParser(
    description="Diagnose access to a product URL"
)
parser.add_argument(
    "--url",
    required=True,
    help="Product URL to diagnose"
)

args = parser.parse_args()
url = args.url

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)

    try:
        page = browser.new_page()
        response = page.goto(url)
        print(f"Final URL: {page.url}")
        print(f"Page title: {page.title()}")

        if response is None:
            print("Verdict: No main response")

        elif response.status != 200:
            print(
                f"Verdict: HTTP error or blocked, "
                f"status={response.status}"
            )

        else:
            print("Verdict: Main response successful")

            cookie_button = page.get_by_role("button", name="Nie zgadzam się")

            try:
                cookie_button.wait_for(state="visible", timeout=3000)
                cookie_button.click()
                cookie_action = "rejected"
            except PlaywrightTimeoutError:
                cookie_action = "not shown"

            price_label = page.get_by_text("cena", exact=True)
            price_container = price_label.locator("..")

            print(f"Status: {response.status}")
            print(f"Cookie action: {cookie_action}")
            print(f"Price block: {price_container.inner_text()}")


    finally:
        browser.close()

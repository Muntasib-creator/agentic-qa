
import re

from playwright.sync_api import Page, expect


TARGET_URL = "https://demo.zeuz.ai/web/level/one/scenerios/login"


def test_login_success(page: Page):
    page.goto(TARGET_URL)

    page.get_by_label("User Name").fill("zeuzTest")
    page.get_by_label("Password").fill("zeuzPass")
    page.get_by_role("button", name="Sign in").click()

    expect(page.locator("body")).to_contain_text(
        re.compile(r"(success|welcome|logged in)", re.IGNORECASE),
        timeout=10_000,
    )


if __name__ == "__main__":
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        test_login_success(page)
        browser.close()

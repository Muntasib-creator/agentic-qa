from __future__ import annotations

from playwright.sync_api import expect, sync_playwright


URL = "https://demo.zeuz.ai/web/level/one/actions/save_text"
SUCCESS_MESSAGE = "You have successfully verified the text"


def test_zeuz_save_text() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        page = browser.new_page()

        try:
            page.goto(URL, wait_until="domcontentloaded")

            prompt_text = page.locator("#randomText")
            input_box = page.locator("#enter_text")
            verify_button = page.get_by_role("button", name="Verify")
            success_message = page.locator("#text_showing")

            expect(prompt_text).to_be_visible()
            text_to_submit = (prompt_text.text_content() or "").strip()
            assert text_to_submit, "Expected the bold text above the input box to be non-empty"

            input_box.fill(text_to_submit)
            expect(input_box).to_have_value(text_to_submit)

            verify_button.click()

            expect(success_message).to_be_visible()
            expect(success_message).to_have_text(SUCCESS_MESSAGE)
        finally:
            browser.close()


if __name__ == "__main__":
    test_zeuz_save_text()
    print("Passed: test_zeuz_save_text")

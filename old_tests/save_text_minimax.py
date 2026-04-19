from playwright.sync_api import sync_playwright


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        page.goto("https://demo.zeuz.ai/web/level/one/actions/save_text")

        random_text = page.locator("#randomText").inner_text()

        page.fill("#enter_text", random_text)

        page.click("#verify_id")

        success_message = page.locator("#text_showing").inner_text()

        assert "You have successfully verified the text" in success_message, f"Expected success message, got: {success_message}"

        browser.close()


if __name__ == "__main__":
    main()
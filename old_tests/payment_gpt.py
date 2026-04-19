from playwright.sync_api import expect, sync_playwright


def parse_price(price_text: str) -> float:
    return float(price_text.replace("$", "").strip())


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        try:
            page.goto(
                "https://demo.zeuz.ai/web/level/two/test/web_level_two_scenerio_payment_form",
                wait_until="domcontentloaded",
            )

            expect(page.get_by_role("heading", name="Payment Checkout Test")).to_be_visible()

            item_price_texts = page.locator("li .text-muted.price").all_inner_texts()
            item_prices = [parse_price(price_text) for price_text in item_price_texts]
            displayed_total = parse_price(page.locator("#total").inner_text())

            assert sum(item_prices) == displayed_total, (
                f"Expected cart total {displayed_total} to match summed item prices {sum(item_prices)}"
            )

            page.fill("#firstName", "John")
            page.fill("#lastName", "Doe")
            page.fill("#username", "johndoe")
            page.fill("#email", "john.doe@example.com")
            page.fill("#address", "123 Main St")
            page.fill("#address2", "Apartment 4B")
            page.select_option("#country", label="United States")
            page.select_option("#state", label="California")
            page.fill("#zip", "90210")

            assert page.locator("#country").input_value() == "United States"
            assert page.locator("#state").input_value() == "California"

            page.locator('label[for="same-address"]').click()
            page.locator('label[for="save-info"]').click()

            assert page.locator("#same-address").is_checked()
            assert page.locator("#save-info").is_checked()

            page.fill("#cc-name", "John Doe")
            page.fill("#cc-number", "4111111111111111")
            page.fill("#cc-expiration", "30/04/2026")
            page.locator("#cc-expiration").blur()
            page.fill("#cc-cvv", "123")

            # Clicking another field closes the jQuery datepicker so checkout is clickable.
            page.locator("#cc-cvv").click()

            page.click("#btnSubmit")

            expect(page.locator("#text_showing")).to_have_text("Registration Successful")
        finally:
            input('exit?')
            browser.close()


if __name__ == "__main__":
    main()

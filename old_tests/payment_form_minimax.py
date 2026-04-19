from playwright.sync_api import sync_playwright


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        page.goto("https://demo.zeuz.ai/web/level/two/test/web_level_two_scenerio_payment_form")
        page.wait_for_load_state("networkidle")

        items = page.locator(".list-group-item").all()[:3]
        prices = []
        for item in items:
            price_elem = item.locator(".price")
            if price_elem.count() > 0:
                price_text = price_elem.inner_text().strip()
                if price_text.startswith("$"):
                    prices.append(int(price_text.replace("$", "")))
        print(f"Item prices: {prices}")

        total_price_text = page.locator("#total").inner_text()
        print(f"Total price text: {total_price_text}")

        calculated_total = sum(prices)
        print(f"Calculated total: {calculated_total}")

        assert calculated_total == int(total_price_text.replace("$", "")), f"Sum of items {calculated_total} does not match total {total_price_text}"

        page.fill("#firstName", "John")
        page.fill("#lastName", "Doe")
        page.fill("#username", "johndoe")
        page.fill("#email", "john@example.com")
        page.fill("#address", "123 Main St")
        page.fill("#address2", "Apt 4")
        page.select_option("#country", "United States")
        page.select_option("#state", "California")
        page.fill("#zip", "12345")
        page.fill("#cc-name", "John Doe")
        page.fill("#cc-number", "4111111111111111")
        page.fill("#cc-expiration", "12/28")
        page.fill("#cc-cvv", "123")

        page.click("#btnSubmit")

        success_message = page.locator("#text_showing").inner_text()
        print(f"Success message: {success_message}")

        assert "Registration Successful" in success_message, f"Expected success message, got: {success_message}"

        input('exit?')
        browser.close()


if __name__ == "__main__":
    main()
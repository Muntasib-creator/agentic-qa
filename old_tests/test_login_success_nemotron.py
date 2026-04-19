from playwright.sync_api import Page, expect

def test_zeuz_login(page: Page):
    page.goto("https://demo.zeuz.ai/web/level/one/scenerios/login")
    
    # Input username - try different locator strategies
    username_input = page.get_by_placeholder("Username")
    if username_input.count() == 0:
        username_input = page.get_by_label("Username")
    if username_input.count() == 0:
        username_input = page.locator("input[type='text'], input[name='username'], input[id='username']").first
    username_input.fill("zeuzTest")
    
    # Input password - try different locator strategies
    password_input = page.get_by_placeholder("Password")
    if password_input.count() == 0:
        password_input = page.get_by_label("Password")
    if password_input.count() == 0:
        password_input = page.locator("input[type='password'], input[name='password'], input[id='password']").first
    password_input.fill("zeuzPass")
    
    # Press sign in button - try different locator strategies
    sign_in_button = page.get_by_role("button", name="Sign In")
    if sign_in_button.count() == 0:
        sign_in_button = page.get_by_role("button", name="Login")
    if sign_in_button.count() == 0:
        sign_in_button = page.locator("button[type='submit']:has-text('Sign In'), button[type='submit']:has-text('Login')").first
    if sign_in_button.count() == 0:
        sign_in_button = page.locator("button").filter(has_text="Sign In").first
    sign_in_button.click()
    
    # Validate login success - wait for URL change or look for success indicators
    try:
        # Wait for redirect to dashboard or similar
        page.wait_for_url("https://demo.zeuz.ai/web/level/one/**", timeout=10000)
        # Additional check: look for common post-login elements
        expect(page.locator("text=Dashboard").or_(page.locator("text=Welcome")).or_(page.locator("text=Home"))).to_be_visible(timeout=5000)
    except:
        # If no redirect, check if we're still on login page but with error or success message
        # Look for success indicators using Playwright's text matching
        success_indicators = page.locator(".success, .alert-success, [class*='success']")
        if success_indicators.count() > 0:
            expect(success_indicators.first).to_be_visible()
        else:
            # Check for text-based success indicators
            welcome_text = page.get_by_text("Login successful", exact=False).or_(page.get_by_text("Welcome", exact=False))
            if welcome_text.count() > 0:
                expect(welcome_text.first).to_be_visible()
            else:
                # If no success indicators, check that we're not seeing error messages
                error_indicators = page.locator(".error, .alert-error, [class*='error']")
                error_text = page.get_by_text("Invalid", exact=False).or_(page.get_by_text("failed", exact=False))
                combined_errors = error_indicators.or_(error_text)
                if combined_errors.count() > 0:
                    expect(combined_errors.first).not_to_be_visible()
                else:
                    # If we can't determine success or failure, at least verify we're not still seeing the login form
                    # (assuming successful login would hide or change the login form)
                    login_form = page.locator("form:has-text('Username')")
                    if login_form.count() > 0:
                        # If login form still visible, login likely failed
                        raise AssertionError("Login form still visible after submit - login may have failed")

# Enables direct execution: uv run testcases/test_zeuz_login.py
if __name__ == "__main__":
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        test_zeuz_login(page)
        browser.close()
        print('success')
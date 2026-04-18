import re

from playwright.sync_api import Page, expect


LOGIN_URL = "https://demo.zeuz.ai/web/level/one/scenerios/login"


def test_login_success(page: Page) -> None:
    page.goto(LOGIN_URL)

    username_input = page.get_by_label(re.compile(r"user name", re.I))
    password_input = page.get_by_label(re.compile(r"password", re.I))
    sign_in_button = page.get_by_role("button", name=re.compile(r"^sign in$", re.I))

    expect(page.get_by_text("Login Scenario")).to_be_visible()
    expect(username_input).to_be_visible()
    expect(password_input).to_be_visible()

    username_input.fill("zeuzTest")
    password_input.fill("zeuzPass")
    sign_in_button.click()
    page.wait_for_load_state("networkidle")

    # The demo may either redirect or replace the login form with a success view.
    # Treat either outcome as a successful login.
    success_markers = [
        page.get_by_text(re.compile(r"login success", re.I)),
        page.get_by_text(re.compile(r"successfully logged in", re.I)),
        page.get_by_text(re.compile(r"\bwelcome\b", re.I)),
        page.get_by_text(re.compile(r"\bdashboard\b", re.I)),
    ]
    login_prompt = page.get_by_text("Enter Username and Password")

    assert any(marker.is_visible() for marker in success_markers) or (
        not login_prompt.is_visible() and not sign_in_button.is_visible()
    )

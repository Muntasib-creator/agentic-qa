from get_driver import get_url
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    ws_url = get_url()
    browser = p.chromium.connect_over_cdp(ws_url)
    context = browser.contexts[0] if browser.contexts else browser.new_context()
    page = context.pages[0] if context.pages else context.new_page()
    page.goto("https://example.com")
    print(page.title())
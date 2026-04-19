import urllib.parse
import urllib.request
from playwright.sync_api import sync_playwright, Browser


def get_driver(headless: bool, session: None | str = None) -> Browser:
    params = {"headless": str(headless).lower()}
    if session is not None:
        params["session"] = session

    url = f"http://localhost:1234/get_driver?{urllib.parse.urlencode(params)}"
    ws_url = urllib.request.urlopen(url).read().decode().strip()

    with sync_playwright() as p:
        return p.chromium.connect_over_cdp(ws_url)
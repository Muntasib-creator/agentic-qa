import json
import urllib.parse
import urllib.request
from playwright.sync_api import sync_playwright, Browser


def get_driver(headless: bool, session: None | str = None) -> Browser:
    params = {"headless": str(headless).lower()}
    if session is not None:
        params["session"] = session

    url = f"http://localhost:1234/get_driver?{urllib.parse.urlencode(params)}"
    response = urllib.request.urlopen(url).read().decode()
    data = json.loads(response)
    ws_url = data["url"]

    print(f"[get_driver] url={ws_url}, session={data['session']}, headless={data['headless']}")

    with sync_playwright() as p:
        return p.chromium.connect_over_cdp(ws_url)
import json
import urllib.parse
import urllib.request

SERVER_HOST = "192.168.1.101"
# SERVER_HOST = "localhost"


def get_url(headless: bool = False, session: None | str = None) -> str:
    params = {"headless": str(headless).lower()}
    if session is not None:
        params["session"] = session

    url = f"http://{SERVER_HOST}:1234/get_driver?{urllib.parse.urlencode(params)}"
    response = urllib.request.urlopen(url).read().decode()
    data = json.loads(response)
    ws_url = data["url"]
    return ws_url
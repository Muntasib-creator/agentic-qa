import json
import socket
import threading
import time
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path


SESSIONS_FILE = Path("sessions.json")
HOST = '192.168.1.101'
FIXED_PORT = 9222
MAX_AGE_MINUTES = 10


BROWSER_THREAD = None
BROWSER_HOLDER = {}


def load_session() -> dict | None:
    if SESSIONS_FILE.exists():
        data = json.loads(SESSIONS_FILE.read_text())
        return data.get("session_9222")
    return None


def save_session(data: dict) -> None:
    SESSIONS_FILE.write_text(json.dumps({"session_9222": data}, indent=2))


def is_thread_alive(tid: int | None) -> bool:
    global BROWSER_THREAD
    if not tid or not BROWSER_THREAD:
        return False
    return BROWSER_THREAD.is_alive()


def is_session_expired(launched_at: str) -> bool:
    try:
        dt = datetime.fromisoformat(launched_at)
        return datetime.now() - dt > timedelta(minutes=MAX_AGE_MINUTES)
    except Exception:
        return True


def wait_for_port(port: int, timeout: float = 10.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            try:
                sock.connect(("127.0.0.1", port))
                return True
            except OSError:
                time.sleep(0.1)
    return False


def browser_worker(port: int, headless: bool, browser_holder: dict) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=[
                f"--remote-debugging-port={port}",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-popup-blocking",
                "--disable-dev-shm-usage",
                "--disable-background-networking",
            ],
        )
        browser_holder["browser"] = browser
        try:
            while browser.is_connected():
                time.sleep(1)
        finally:
            browser.close()


def launch_browser(port: int, headless: bool) -> int | None:
    global BROWSER_THREAD, BROWSER_HOLDER
    BROWSER_HOLDER = {}
    BROWSER_THREAD = threading.Thread(
        target=browser_worker,
        args=(port, headless, BROWSER_HOLDER),
        daemon=True,
    )
    BROWSER_THREAD.start()
    if not wait_for_port(port):
        return None
    while "browser" not in BROWSER_HOLDER:
        time.sleep(0.1)
    return BROWSER_THREAD.ident


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/get_driver"):
            self.handle_get_driver()
        else:
            self.send_error(404)

    def handle_get_driver(self):
        from urllib.parse import parse_qs, urlparse

        query = parse_qs(urlparse(self.path).query)
        headless = query.get("headless", ["false"])[0].lower() == "true"

        existing = load_session()
        tid = existing.get("tid") if existing else None
        launched_at = existing.get("launched_at") if existing else None

        if tid and is_thread_alive(tid):
            if launched_at and is_session_expired(launched_at):
                print(f"[server] Session expired, relaunching browser on port {FIXED_PORT}")
            else:
                ws_url = f"http://{HOST}:{FIXED_PORT}"
                print(f"[server] Reusing existing session on port {FIXED_PORT}")
                response = json.dumps({
                    "url": ws_url,
                    "session": "session_9222",
                    "port": FIXED_PORT,
                    "headless": existing["headless"],
                    "launched_at": launched_at,
                }).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(response)
                return

        tid = launch_browser(FIXED_PORT, headless)
        if not tid:
            self.send_error(500, "Failed to launch browser")
            return

        now = datetime.now().isoformat()
        ws_url = f"http://{HOST}:{FIXED_PORT}"
        save_session({
            "port": FIXED_PORT,
            "headless": headless,
            "tid": tid,
            "launched_at": now,
        })

        print(f"[server] Launched browser session on port {FIXED_PORT} (headless={headless})")

        response = json.dumps({
            "url": ws_url,
            "session": "session_9222",
            "port": FIXED_PORT,
            "headless": headless,
            "launched_at": now,
        }).encode()

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format, *args):
        print(f"[server] {args[0]}")


def run_server(host: str = "0.0.0.0", port: int = 1234):
    server = HTTPServer((host, port), Handler)
    print(f"[server] Listening on {host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
import json
import os
import socket
import threading
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path


SESSIONS_FILE = Path("sessions.json")
BASE_PORT = 9222
MAX_PORT = 9232


def find_available_port(start: int, end: int) -> int | None:
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return None


def load_sessions() -> dict:
    if SESSIONS_FILE.exists():
        return json.loads(SESSIONS_FILE.read_text())
    return {}


def save_sessions(sessions: dict) -> None:
    SESSIONS_FILE.write_text(json.dumps(sessions, indent=2))


BROWSER_THREADS = {}


def is_thread_alive(tid: int | None) -> bool:
    if not tid or tid not in BROWSER_THREADS:
        return False
    thread = BROWSER_THREADS[tid]
    return thread.is_alive()


def wait_for_port(host: str, port: int, timeout: float = 10.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            try:
                sock.connect((host, port))
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
    browser_holder = {}
    thread = threading.Thread(
        target=browser_worker,
        args=(port, headless, browser_holder),
        daemon=True,
    )
    thread.start()
    if not wait_for_port("127.0.0.1", port):
        return None
    while "browser" not in browser_holder:
        time.sleep(0.1)
    BROWSER_THREADS[thread.ident] = thread
    return thread.ident


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
        session = query.get("session", [None])[0]

        if session:
            sessions = load_sessions()
            data = sessions.get(session)
            if data and is_thread_alive(data.get("tid")):
                ws_url = f"http://localhost:{data['port']}"
                print(f"[server] Reusing existing session {session} on port {data['port']}")
                response = json.dumps({
                    "url": ws_url,
                    "session": session,
                    "port": data["port"],
                    "headless": data["headless"],
                    "launched_at": data["launched_at"],
                }).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(response)
                return
            if data:
                del sessions[session]
                save_sessions(sessions)

        port = find_available_port(BASE_PORT, MAX_PORT)
        if not port:
            self.send_error(500, "No available port")
            return

        tid = launch_browser(port, headless)
        if not tid:
            self.send_error(500, "Failed to launch browser")
            return

        ws_url = f"http://localhost:{port}"
        session_id = f"session_{port}"
        sessions = load_sessions()
        sessions[session_id] = {
            "port": port,
            "headless": headless,
            "tid": tid,
            "launched_at": datetime.now().isoformat(),
        }
        save_sessions(sessions)

        print(f"[server] Launched browser session {session_id} on port {port} (headless={headless})")

        response = json.dumps({
            "url": ws_url,
            "session": session_id,
            "port": port,
            "headless": headless,
            "launched_at": sessions[session_id]["launched_at"],
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

import json
import socket
import subprocess
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


def launch_browser(port: int, headless: bool) -> subprocess.Popen:
    args = [
        "google-chrome",
        f"--remote-debugging-port={port}",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    if headless:
        args.extend(["--headless", "--disable-gpu", "--no-sandbox"])
    return subprocess.Popen(args)


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
            if data:
                ws_url = f"http://localhost:{data['port']}"
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(ws_url.encode())
                return

        port = find_available_port(BASE_PORT, MAX_PORT)
        if not port:
            self.send_error(500, "No available port")
            return

        launch_browser(port, headless)

        ws_url = f"http://localhost:{port}"
        session_id = f"session_{port}"
        sessions = load_sessions()
        sessions[session_id] = {"port": port, "headless": headless}
        save_sessions(sessions)

        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(ws_url.encode())

    def log_message(self, format, *args):
        print(f"[server] {args[0]}")


def run_server(host: str = "0.0.0.0", port: int = 1234):
    server = HTTPServer((host, port), Handler)
    print(f"[server] Listening on {host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
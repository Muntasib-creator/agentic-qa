from __future__ import annotations

import argparse
import importlib.util
import json
import os
import socket
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

from testcases.runtime import Step, StepRunError, execute_steps, run_full_validation, slugify


DEFAULT_ARTIFACTS_DIR = Path("testcases/.artifacts")
SESSION_DIR = Path(tempfile.gettempdir()) / "agentic_qa_sessions"


def session_name_for_test(test_path: str) -> str:
    return slugify(Path(test_path).stem)


def session_file_path(session_name: str) -> Path:
    return SESSION_DIR / f"{session_name}.json"


def socket_path_for_session(session_name: str) -> Path:
    return SESSION_DIR / f"{session_name}.sock"


def load_test_steps(test_path: str) -> tuple[str, list[Step]]:
    module_name = f"agentic_qa_{slugify(Path(test_path).stem)}_{time.time_ns()}"
    spec = importlib.util.spec_from_file_location(module_name, test_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load test module from {test_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    build_steps = getattr(module, "build_steps", None)
    if build_steps is None:
        raise RuntimeError(f"{test_path} does not define build_steps()")

    steps = build_steps()
    if not steps:
        raise RuntimeError(f"{test_path} returned no steps")
    return Path(test_path).stem, steps


class RunnerSession:
    def __init__(self, *, test_path: str, headed: bool, artifacts_dir: str) -> None:
        self.test_path = str(Path(test_path).resolve())
        self.test_name = Path(test_path).stem
        self.headed = headed
        self.artifacts_dir = artifacts_dir
        self.session_state: dict[str, Any] = {}
        self.completed_steps: list[str] = []
        self._playwright_cm = sync_playwright()
        self.playwright: Playwright = self._playwright_cm.start()
        self.browser: Browser = self.playwright.chromium.launch(headless=not headed)
        self.context: BrowserContext
        self.page: Page
        self._create_page()

    def _create_page(self) -> None:
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        self.session_state = {}
        self.completed_steps = []

    def cleanup(self) -> None:
        self.context.close()
        self.browser.close()
        self.playwright.stop()

    def reset(self) -> None:
        self.context.close()
        self._create_page()

    def status(self) -> dict[str, Any]:
        return {
            "test_path": self.test_path,
            "headed": self.headed,
            "artifacts_dir": self.artifacts_dir,
            "completed_steps": self.completed_steps,
            "current_url": self.page.url,
        }

    def run_step(self, step_ref: str) -> dict[str, Any]:
        _, steps = load_test_steps(self.test_path)
        target_index = resolve_step_ref(steps, step_ref)
        expected_index = len(self.completed_steps) + 1

        if target_index != expected_index:
            raise RuntimeError(
                f"Step {target_index} requested, but next runnable step is {expected_index}. "
                "Use the same live session in order or reset the session."
            )

        result = execute_steps(
            context=self.context,
            page=self.page,
            steps=steps,
            session_state=self.session_state,
            start_index=target_index,
            end_index=target_index,
            test_name=self.test_name,
            artifacts_dir=self.artifacts_dir,
            trace_label=f"step-{target_index:02d}-{steps[target_index - 1].name}",
        )
        self.completed_steps.append(steps[target_index - 1].name)
        result["mode"] = "step"
        result["step_index"] = target_index
        result["step_name"] = steps[target_index - 1].name
        return result

    def run_full(self) -> dict[str, Any]:
        _, steps = load_test_steps(self.test_path)
        next_index = len(self.completed_steps) + 1
        if next_index > len(steps):
            return {
                "mode": "full",
                "message": "All steps already completed in the live session.",
                "completed_steps": self.completed_steps,
            }

        result = execute_steps(
            context=self.context,
            page=self.page,
            steps=steps,
            session_state=self.session_state,
            start_index=next_index,
            end_index=len(steps),
            test_name=self.test_name,
            artifacts_dir=self.artifacts_dir,
            trace_label=f"full-from-step-{next_index:02d}",
        )
        self.completed_steps = [step.name for step in steps]
        result["mode"] = "full"
        result["start_index"] = next_index
        result["end_index"] = len(steps)
        return result

    def validate_full(self, repeat: int) -> dict[str, Any]:
        _, steps = load_test_steps(self.test_path)
        result = run_full_validation(
            browser=self.browser,
            steps=steps,
            test_name=self.test_name,
            artifacts_dir=self.artifacts_dir,
            repeat=repeat,
        )
        return {"mode": "validate-full", "repeat": repeat, "results": result}


def resolve_step_ref(steps: list[Step], step_ref: str) -> int:
    if step_ref.isdigit():
        index = int(step_ref)
        if 1 <= index <= len(steps):
            return index
        raise RuntimeError(f"Step index {index} is out of range 1..{len(steps)}")

    for index, step in enumerate(steps, start=1):
        if step.name == step_ref:
            return index

    raise RuntimeError(f"Unknown step {step_ref!r}")


class RunnerRequestHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        request = json.loads(self.rfile.readline().decode("utf-8"))
        try:
            response = self.server.runner.handle_command(request)  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001
            if isinstance(exc, StepRunError):
                payload = exc.to_dict()
            else:
                payload = {"message": str(exc)}
            response = {"ok": False, "error": payload}
        self.wfile.write((json.dumps(response) + "\n").encode("utf-8"))


class RunnerServer(socketserver.UnixStreamServer):
    allow_reuse_address = True

    def __init__(self, socket_path: str, runner: "SessionDaemon") -> None:
        self.runner = runner
        socket_file = Path(socket_path)
        if socket_file.exists():
            socket_file.unlink()
        super().__init__(socket_path, RunnerRequestHandler)


class SessionDaemon:
    def __init__(self, *, test_path: str, headed: bool, artifacts_dir: str, session_file: Path, socket_path: Path) -> None:
        self.session_file = session_file
        self.socket_path = socket_path
        self.runner_session = RunnerSession(test_path=test_path, headed=headed, artifacts_dir=artifacts_dir)
        self.server = RunnerServer(str(socket_path), self)

    def handle_command(self, request: dict[str, Any]) -> dict[str, Any]:
        command = request["command"]
        if command == "status":
            return {"ok": True, "result": self.runner_session.status()}
        if command == "run-step":
            return {"ok": True, "result": self.runner_session.run_step(request["step"])}
        if command == "run-full":
            return {"ok": True, "result": self.runner_session.run_full()}
        if command == "validate-full":
            return {"ok": True, "result": self.runner_session.validate_full(int(request.get("repeat", 1)))}
        if command == "reset":
            self.runner_session.reset()
            return {"ok": True, "result": self.runner_session.status()}
        if command == "stop":
            result = self.runner_session.status()
            threading.Thread(target=self.shutdown_server, daemon=True).start()
            return {"ok": True, "result": result}
        raise RuntimeError(f"Unknown command: {command}")

    def serve(self) -> None:
        SESSION_DIR.mkdir(parents=True, exist_ok=True)
        self.session_file.write_text(
            json.dumps(
                {
                    "pid": os.getpid(),
                    "socket_path": str(self.socket_path),
                    "test_path": self.runner_session.test_path,
                    "headed": self.runner_session.headed,
                    "artifacts_dir": self.runner_session.artifacts_dir,
                }
            ),
            encoding="utf-8",
        )
        try:
            self.server.serve_forever()
        finally:
            self.cleanup()

    def shutdown_server(self) -> None:
        self.server.shutdown()

    def cleanup(self) -> None:
        self.server.server_close()
        self.runner_session.cleanup()
        if self.socket_path.exists():
            self.socket_path.unlink()
        if self.session_file.exists():
            self.session_file.unlink()


def send_command(session_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    session_file = session_file_path(session_name)
    if not session_file.exists():
        raise RuntimeError(f"No active session named {session_name}. Start one first.")

    session_info = json.loads(session_file.read_text(encoding="utf-8"))
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.connect(session_info["socket_path"])
        sock.sendall((json.dumps(payload) + "\n").encode("utf-8"))

        buffer = b""
        while not buffer.endswith(b"\n"):
            chunk = sock.recv(8192)
            if not chunk:
                break
            buffer += chunk
    finally:
        sock.close()

    if not buffer:
        raise RuntimeError("Session runner did not return a response.")
    return json.loads(buffer.decode("utf-8"))


def print_response(response: dict[str, Any]) -> int:
    if response.get("ok"):
        print(json.dumps(response["result"], indent=2))
        return 0

    print(json.dumps(response["error"], indent=2), file=sys.stderr)
    return 1


def start_session(test_path: str, session_name: str | None, headed: bool, artifacts_dir: str) -> int:
    resolved_test = str(Path(test_path).resolve())
    session_name = session_name or session_name_for_test(resolved_test)
    session_file = session_file_path(session_name)
    socket_path = socket_path_for_session(session_name)
    log_path = SESSION_DIR / f"{session_name}.log"

    SESSION_DIR.mkdir(parents=True, exist_ok=True)

    if session_file.exists():
        raise RuntimeError(f"Session {session_name} already exists. Stop it or use a different name.")

    command = [
        sys.executable,
        "-m",
        "testcases.session_runner",
        "_serve",
        "--test",
        resolved_test,
        "--session-file",
        str(session_file),
        "--socket-path",
        str(socket_path),
        "--artifacts-dir",
        artifacts_dir,
    ]
    if headed:
        command.append("--headed")

    with log_path.open("a", encoding="utf-8") as log_file:
        subprocess.Popen(  # noqa: S603
            command,
            stdout=log_file,
            stderr=log_file,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            cwd=str(Path.cwd()),
        )

    deadline = time.time() + 15
    while time.time() < deadline:
        if session_file.exists() and socket_path.exists():
            response = send_command(session_name, {"command": "status"})
            return print_response(response)
        time.sleep(0.2)

    raise RuntimeError(f"Timed out waiting for session {session_name} to start. Check {log_path}.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Persistent Playwright session runner for incremental testcase authoring.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start", help="Start a persistent Playwright session for a testcase.")
    start.add_argument("--test", required=True, help="Path to the testcase file.")
    start.add_argument("--session-name", help="Optional explicit session name.")
    start.add_argument("--headed", action="store_true", help="Launch a headed browser.")
    start.add_argument("--artifacts-dir", default=str(DEFAULT_ARTIFACTS_DIR), help="Artifact root directory.")

    run_step = subparsers.add_parser("run-step", help="Run the next step in the live session.")
    run_step.add_argument("--session-name", required=True, help="Session name returned by start.")
    run_step.add_argument("--step", required=True, help="1-based step index or exact step name.")

    run_full = subparsers.add_parser("run-full", help="Run all remaining steps in the live session.")
    run_full.add_argument("--session-name", required=True, help="Session name returned by start.")

    validate_full = subparsers.add_parser("validate-full", help="Run a clean full validation in fresh contexts.")
    validate_full.add_argument("--session-name", required=True, help="Session name returned by start.")
    validate_full.add_argument("--repeat", type=int, default=3, help="Number of clean validation runs.")

    status = subparsers.add_parser("status", help="Show live session status.")
    status.add_argument("--session-name", required=True, help="Session name returned by start.")

    reset = subparsers.add_parser("reset", help="Reset the page and state inside the live session.")
    reset.add_argument("--session-name", required=True, help="Session name returned by start.")

    stop = subparsers.add_parser("stop", help="Stop a live session.")
    stop.add_argument("--session-name", required=True, help="Session name returned by start.")

    serve = subparsers.add_parser("_serve", help=argparse.SUPPRESS)
    serve.add_argument("--test", required=True)
    serve.add_argument("--session-file", required=True)
    serve.add_argument("--socket-path", required=True)
    serve.add_argument("--artifacts-dir", required=True)
    serve.add_argument("--headed", action="store_true")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "start":
        return start_session(args.test, args.session_name, args.headed, args.artifacts_dir)

    if args.command == "_serve":
        daemon = SessionDaemon(
            test_path=args.test,
            headed=args.headed,
            artifacts_dir=args.artifacts_dir,
            session_file=Path(args.session_file),
            socket_path=Path(args.socket_path),
        )
        daemon.serve()
        return 0

    payload: dict[str, Any] = {"command": args.command}
    session_name = args.session_name

    if args.command == "run-step":
        payload["step"] = args.step
    elif args.command == "validate-full":
        payload["repeat"] = args.repeat

    response = send_command(session_name, payload)
    return print_response(response)


if __name__ == "__main__":
    raise SystemExit(main())

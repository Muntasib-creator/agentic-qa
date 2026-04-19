from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from playwright.sync_api import Browser, BrowserContext, Page


StepFunc = Callable[[Page, dict[str, Any]], None]


@dataclass(frozen=True)
class Step:
    name: str
    action: StepFunc
    check: StepFunc


@dataclass(frozen=True)
class StepRunError(Exception):
    step_index: int
    step_name: str
    phase: str
    message: str
    screenshot_path: str | None = None
    html_path: str | None = None
    trace_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_index": self.step_index,
            "step_name": self.step_name,
            "phase": self.phase,
            "message": self.message,
            "screenshot_path": self.screenshot_path,
            "html_path": self.html_path,
            "trace_path": self.trace_path,
        }


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return normalized or "step"


def artifact_root(base_dir: str | Path, test_name: str) -> Path:
    path = Path(base_dir) / slugify(test_name)
    path.mkdir(parents=True, exist_ok=True)
    return path


def run_artifact_dir(base_dir: str | Path, test_name: str, label: str) -> Path:
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    path = artifact_root(base_dir, test_name) / f"{timestamp}-{slugify(label)}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def capture_failure_artifacts(
    page: Page,
    run_dir: Path,
    *,
    step_index: int,
    step_name: str,
    phase: str,
    message: str,
    trace_path: str | None,
) -> StepRunError:
    prefix = f"step-{step_index:02d}-{slugify(step_name)}-{phase}"
    screenshot_path = run_dir / f"{prefix}.png"
    html_path = run_dir / f"{prefix}.html"
    metadata_path = run_dir / f"{prefix}.json"

    page.screenshot(path=str(screenshot_path), full_page=True)
    html_path.write_text(page.content(), encoding="utf-8")
    metadata_path.write_text(
        json.dumps(
            {
                "step_index": step_index,
                "step_name": step_name,
                "phase": phase,
                "message": message,
                "url": page.url,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    return StepRunError(
        step_index=step_index,
        step_name=step_name,
        phase=phase,
        message=message,
        screenshot_path=str(screenshot_path),
        html_path=str(html_path),
        trace_path=trace_path,
    )


def execute_steps(
    *,
    context: BrowserContext,
    page: Page,
    steps: list[Step],
    session_state: dict[str, Any],
    start_index: int,
    end_index: int,
    test_name: str,
    artifacts_dir: str | Path,
    trace_label: str,
) -> dict[str, Any]:
    run_dir = run_artifact_dir(artifacts_dir, test_name, trace_label)
    trace_path = run_dir / f"{slugify(trace_label)}.zip"
    context.tracing.start(screenshots=True, snapshots=True, sources=True)

    try:
        for index in range(start_index, end_index + 1):
            step = steps[index - 1]

            try:
                step.action(page, session_state)
            except Exception as exc:  # noqa: BLE001
                raise capture_failure_artifacts(
                    page,
                    run_dir,
                    step_index=index,
                    step_name=step.name,
                    phase="action",
                    message=str(exc),
                    trace_path=str(trace_path),
                ) from exc

            try:
                step.check(page, session_state)
            except Exception as exc:  # noqa: BLE001
                raise capture_failure_artifacts(
                    page,
                    run_dir,
                    step_index=index,
                    step_name=step.name,
                    phase="check",
                    message=str(exc),
                    trace_path=str(trace_path),
                ) from exc
    except Exception:
        context.tracing.stop(path=str(trace_path))
        raise

    context.tracing.stop(path=str(trace_path))
    return {
        "run_dir": str(run_dir),
        "trace_path": str(trace_path),
        "completed_steps": [step.name for step in steps[start_index - 1 : end_index]],
    }


def run_full_validation(
    *,
    browser: Browser,
    steps: list[Step],
    test_name: str,
    artifacts_dir: str | Path,
    repeat: int = 1,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    for attempt in range(1, repeat + 1):
        context = browser.new_context()
        page = context.new_page()
        session_state: dict[str, Any] = {}

        try:
            result = execute_steps(
                context=context,
                page=page,
                steps=steps,
                session_state=session_state,
                start_index=1,
                end_index=len(steps),
                test_name=test_name,
                artifacts_dir=artifacts_dir,
                trace_label=f"full-attempt-{attempt}",
            )
            result["attempt"] = attempt
            results.append(result)
        finally:
            context.close()

    return results

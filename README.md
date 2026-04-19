# agentic-qa

This repository is a small Playwright Python workspace for authoring browser automation testcases against an external application under test.

## Incremental authoring workflow
Use the persistent session runner to keep one browser session alive while building a testcase step by step:

```bash
uv run python -m testcases.session_runner start --test testcases/test_login_success.py --session-name login --headed
uv run python -m testcases.session_runner run-step --session-name login --step 1
uv run python -m testcases.session_runner run-step --session-name login --step 2
uv run python -m testcases.session_runner run-full --session-name login
uv run python -m testcases.session_runner validate-full --session-name login --repeat 3
uv run python -m testcases.session_runner stop --session-name login
```

Artifacts are written under `testcases/.artifacts/`.

## Direct full validation
Each testcase should also support a direct clean run from scratch:

```bash
uv run python testcases/test_login_success.py --repeat 3
```

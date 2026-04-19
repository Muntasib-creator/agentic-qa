# agentic-qa

This repository is a small Playwright Python workspace for authoring browser automation testcases against an external application under test.

## Incremental authoring workflow
Use the already-running browser on `http://localhost:9222` only as a validation scratchpad while building a testcase. Validate partial snippets there, inspect the DOM with `page.content()`, and only then write the final testcase.

```bash
uv run python - <<'PY'
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    context = browser.contexts[0] if browser.contexts else browser.new_context()
    page = context.pages[0] if context.pages else context.new_page()
    page.goto("https://example.com")
    html = page.content()
    print(html)
PY
```

Build locators from the live DOM returned by the page.

## Direct full validation
Each final testcase should launch its own Playwright browser and support a direct run from scratch:

```bash
uv run python testcases/test_login_success.py
```

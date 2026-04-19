# Test Case Generation Guide for CLI Agents

## Required Authoring Workflow
When creating or editing test cases, assume there is already a browser session available at `http://localhost:9222` for validation only. Connect to that live browser with Playwright CDP to try partial code, inspect the live DOM, and refine the flow before writing the final testcase.

Use this workflow:

1. Connect to the browser on `http://192.168.1.101:9222`.
2. Open the target URL or continue from the current live page.
3. Execute only the next small action you want to validate.
4. Read the DOM with `page.content()`.
5. Build or refine locators from the returned HTML and the page's accessible surface.
6. Repeat until each action works.
7. Only then write the final testcase file under `testcases/`.
8. After the entire testcase is written, run the full file with `uv run python testcases/test_<name>.py`.
9. If the full run fails, read the script error carefully, identify the failing step, then go back to partial validation in the live browser on `9222` to reproduce and inspect that step.
10. Use the live DOM and page state to diagnose the problem, fix the testcase, and rerun the full file again.

Do not build or depend on a custom step-runner for authoring.
Do not make the final testcase depend on the browser running on `9222`.
The `9222` browser exists only to validate partial snippets while authoring.

## Partial Validation Snippet
Use snippets like this while exploring or validating one action at a time:

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://192.168.1.101:9222")
    context = browser.contexts[0] if browser.contexts else browser.new_context()
    page = context.pages[0] if context.pages else context.new_page()
    page.goto("https://example.com")
    page.fill("textarea[name='desc']", "hello world")
    html = page.content()
    print(html)
```

Replace `page.goto(...)` and the action under test with the exact step you are validating next. After each meaningful action, call `page.content()` and inspect the HTML before deciding on the next locator.

## Test Case Structure
Each generated testcase should stay simple:

- A normal Playwright Python test under `testcases/`
- Immediate assertions after meaningful UI actions
- The testcase itself should launch its own Playwright browser/context/page
- The testcase should close the browser at the end
- A direct execution block so the file can run with `uv run python testcases/test_<name>.py`

Do not force testcase files into a step-runner framework unless the user explicitly asks for that structure.

## Validation Rules
- Validate actions incrementally in the live browser first.
- Prefer small snippets over writing the whole test up front.
- After navigation or interaction, inspect `page.content()` and adjust locators from the real DOM.
- Treat the live browser on `9222` as a scratchpad only, not as the runtime for the final test file.
- Prefer assertions that prove the page actually changed:
  - visible text
  - form values
  - URL changes
  - enabled or disabled state
  - element visibility
- Once the full flow is written, run the whole testcase end to end with `uv run python testcases/test_<name>.py`.
- If that full run fails, do not blindly edit the full script first. Return to partial validation in the live `9222` browser, reproduce the failing step, inspect the current DOM, fix the issue, and rerun the full file.

## Locator Guidance
Choose locators based on what is actually stable in the live DOM and what keeps the testcase readable. Use the DOM returned by `page.content()` and the visible UI state to decide what works best for that page.

Do not hard-code one locator strategy order into the agent workflow. Pick the most reliable locator for the actual page under test.

## Execution Method
- Partial live-browser validation:
  `uv run python - <<'PY'`
- Connect with:
  `p.chromium.connect_over_cdp("http://192.168.1.101:9222")`
- Collect DOM with:
  `html = page.content()`
- Final full testcase run:
  `uv run python testcases/test_<name>.py`
- Full-run failure loop:
  read the traceback, reproduce the failing step in the live `9222` browser, inspect DOM/state, fix the testcase, rerun the full file

# Test Case Generation Guide for CLI Agents

## Purpose
This repository exists solely to create and maintain Playwright Python test cases for an external application under test (AUT). Test cases reside in this `testcases/` directory. The AUT source code is located in another repository.

## Workflow for CLI Agents
When creating or editing test cases:

### 1. Inspect the LIVE Application
- Ensure the AUT is running (environment already prepared)
- Use browser dev tools to examine current DOM state
- Derive stable locators from: ARIA roles, accessible labels, placeholder text, visible text

### 2. Implement Test Cases
- Create files in `testcases/` with descriptive names (e.g., `test_user_login.py`)
- Use Playwright's synchronous API with this structure:
  ```python
  from playwright.sync_api import Page, expect

  def test_<name>(page: Page):
      page.goto("<TARGET_URL>")
      # Use stable locators prioritized below
      page.get_by_role("button", name="Submit").click()
      expect(page.locator("[data-testid='success-message']")).to_be_visible()

  # Enables direct execution: uv run testcases/test_<name>.py
  if __name__ == "__main__":
      from playwright.sync_api import sync_playwright
      with sync_playwright() as p:
          browser = p.chromium.launch(headless=False)
          page = browser.new_page()
          test_<name>(page)
          browser.close()
  ```

### 3. Validate & Refine
- Run test directly: `uv run testcases/test_<name>.py`
- If failing, re-inspect LIVE DOM (never reuse stale selectors)
- Adjust locators/actions until test passes consistently


## Execution Method
- Run individual test: `uv run testcases/test_filename.py`
- View headed browser: Set `headless=False` in launch() or use `--headed` flag
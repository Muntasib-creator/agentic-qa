# Test Case Generation Guide for CLI Agents

## Purpose
This repository exists solely to create and maintain Playwright Python test cases for an external application under test (AUT). Test cases reside in this `testcases/` directory. The AUT source code is located in another repository.

## Required Authoring Workflow
When creating or editing test cases, use the persistent session runner so one browser session is reused across incremental steps:

1. Inspect the LIVE application.
2. Decide the ordered step list before writing much code.
3. Start a persistent session:
   `uv run python -m testcases.session_runner start --test testcases/test_<name>.py --session-name <name> --headed`
4. Implement only the next step.
5. Run that step in the live session:
   `uv run python -m testcases.session_runner run-step --session-name <name> --step <n>`
6. If the step fails, inspect the saved screenshot / HTML / trace, fix the code, and rerun the same step or reset the session if state is no longer trustworthy.
7. Only after the step passes should you add the next step.
8. After all steps pass individually, run remaining steps in the same live session:
   `uv run python -m testcases.session_runner run-full --session-name <name>`
9. Finish with clean end-to-end validation from a fresh context:
   `uv run python -m testcases.session_runner validate-full --session-name <name> --repeat 3`
10. Stop the persistent session when done:
   `uv run python -m testcases.session_runner stop --session-name <name>`

## Test Case Structure
Each generated testcase must expose:

- `build_steps() -> list[Step]`
- Ordered, human-readable step names
- One focused UI action per step
- One immediate validation per step
- A direct full-validation entrypoint for clean runs

Use Playwright's synchronous API and the shared `Step` type from `testcases.runtime`.

## Step Rules
- Reuse the same persistent browser session while authoring steps.
- Do not write the full test first and debug at the end.
- Do not skip per-step validation.
- Prefer checks that prove the UI actually changed:
  - visible text
  - URL changes
  - form values
  - enabled/disabled state
  - DOM visibility
- If a live session becomes unreliable after a failure, run:
  `uv run python -m testcases.session_runner reset --session-name <name>`

## Execution Method
- Start persistent authoring session:
  `uv run python -m testcases.session_runner start --test testcases/test_<name>.py --session-name <name> --headed`
- Run one step in the existing session:
  `uv run python -m testcases.session_runner run-step --session-name <name> --step 2`
- Continue all remaining steps in the same session:
  `uv run python -m testcases.session_runner run-full --session-name <name>`
- Fresh validation from clean contexts:
  `uv run python -m testcases.session_runner validate-full --session-name <name> --repeat 3`
- Direct full run from scratch for a single testcase:
  `uv run python testcases/test_<name>.py --repeat 3`

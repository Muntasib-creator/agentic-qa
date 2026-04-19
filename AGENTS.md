# Repository Guidelines

## Project Structure & Module Organization
This repository is intentionally small. Keep application code at the top level for now:

- `main.py` - current entry point and runnable example.
- `pyproject.toml` - project metadata and dependency definition.
- `uv.lock` - pinned environment state for `uv`.
- `testcases/` - browser-driven Playwright Python test cases and folder-scoped instructions.

If the project grows, place reusable code in a package directory such as `agentic_qa/` and tests in `tests/`.
For this repo, prefer `testcases/` for generated tests instead of a generic `tests/` directory.

## Build, Test, and Development Commands
Use `uv` for local work:

- `uv sync` - create or update the virtual environment from `pyproject.toml` and `uv.lock`.
- `uv run python main.py` - run the current entry point.
- `uv add <package>` - add a dependency and update project metadata.

There is no dedicated build step or test suite configured yet.

No formatter or linter is configured in `pyproject.toml`; if you add one, document the command here and keep it consistent.

## Testing Guidelines
No automated tests exist yet. When adding test cases for the target application:

- Use Playwright Python.
- Put generated cases under `testcases/`.
- Author them incrementally by connecting Playwright to the already-running browser on `http://localhost:9222` for validation only.
- Validate partial code against the live page and inspect `page.content()` before finalizing locators.
- The final testcase itself should launch and close its own Playwright browser.
- Finish with a full testcase run after the incremental checks succeed.

## Commit & Pull Request Guidelines
This branch has no commit history yet, so there is no established commit convention. Use short, imperative commit subjects, for example: `Add CLI entry point`.

Pull requests should include:

- A concise summary of the change.
- Any relevant issue references.
- Notes on manual verification when behavior changes.

## Agent-Specific Notes
Keep changes minimal and aligned with the current flat layout unless the repository clearly expands into a package structure.
When creating or updating test cases, follow the instructions in `testcases/AGENTS.md`.

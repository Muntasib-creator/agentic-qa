# Repository Guidelines

## Purpose
Use this folder for generated Playwright Python test cases only. Keep artifacts here scoped to browser validation work for the external application under test.

## Workflow
When given a URL and test requirement:

1. Open the page in a browser and inspect the live DOM.
2. Derive stable locators from accessible attributes, roles, labels, and text.
3. Create the Playwright Python testcase in `testcases/` using `playwright.sync_api`
4. Run the testcase in partial steps, then re-read the DOM after each navigation, refresh, modal, or route change.
5. Refine actions, locators, and assertions until the requirement is fully covered.

Treat DOM snapshots as ephemeral. Recollect them after any UI state change instead of reusing stale selectors.

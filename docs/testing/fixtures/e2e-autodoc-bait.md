# E2E autodoc bait fixture

<!-- E2E_AUTODOC_BAIT_MARKER -->

This page is the **live E2E fixture** for `obs:autodoc`.

## Purpose

This file gives docs-patrol one controlled documentation gap so the live E2E flow can verify:

- audit mode opens exactly one autodoc issue for this path; and
- fix mode can propose a documentation PR from that issue.

## How E2E mode targets this file

The framework-only workflow `e2e-trigger-obs-aw-schedule.yml` dispatches `obs-aw-autodoc` with `e2e-autodoc-mode=true`.
That injects `E2E_AUTODOC_MODE=true` platform instructions so docs-patrol evaluates **only** `docs/testing/fixtures/e2e-autodoc-bait.md`, cites this path, and includes `E2E_AUTODOC_BAIT_MARKER` in the issue body.

## Cleanup expectations

After verification, the E2E harness closes the generated issue and closes PRs opened from it.
This fixture remains on the default branch so future live runs keep a stable, repeatable bait target.

See [autodoc-e2e-bait](../autodoc-e2e-bait.md).

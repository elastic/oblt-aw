# E2E autodoc bait fixture

<!-- E2E_AUTODOC_BAIT_MARKER -->

This page is the **live E2E fixture** for `obs:autodoc`.

## Purpose

The live autodoc E2E harness needs a stable, known documentation gap that can be audited without mutating default-branch source files at runtime. This fixture provides that gap for the docs-patrol route and keeps the test deterministic.

## How evaluation works

- `e2e-autodoc.yml` dispatches framework-only `e2e-trigger-obs-aw-schedule.yml`.
- The wrapper forwards `e2e-autodoc-mode=true` into the schedule route.
- In that mode, `obs-aw-autodoc.yml` injects `E2E_AUTODOC_MODE=true` platform instructions that scope docs-patrol to this file only.
- The resulting audit issue cites this path and includes `E2E_AUTODOC_BAIT_MARKER` so the harness can verify the expected behavior.

## Cleanup expectations

- The E2E-generated autodoc issue and fix PR are closed after verification.
- The fixture file remains on the default branch so future E2E runs keep the same target.
- No product documentation or client schedule workflow input is changed by this fixture flow.

See [autodoc-e2e-bait](../autodoc-e2e-bait.md).

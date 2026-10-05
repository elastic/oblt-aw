# E2E autodoc bait (intentional incomplete page)

<!-- E2E_AUTODOC_BAIT_MARKER -->

This page is the **live E2E fixture** for `obs:autodoc`.

## Status

Incomplete on purpose. Do **not** treat this as finished product documentation.

## Purpose of the live autodoc E2E harness

This fixture gives the live autodoc E2E harness a stable, intentional docs gap to audit. The run is expected to find this page incomplete and open exactly one finding that references both this path and `E2E_AUTODOC_BAIT_MARKER`.

## How `e2e-trigger-obs-aw-schedule.yml` / `e2e-autodoc-mode` evaluates this file

When `docs/testing/e2e-autodoc.yml` enables `e2e-autodoc-mode=true`, the control-plane wrapper (`e2e-trigger-obs-aw-schedule.yml`) injects `E2E_AUTODOC_MODE=true` so docs-patrol audits only this fixture path instead of regular docs content.

## Cleanup expectations

Live E2E follow-up issue/PR artifacts are closed during cleanup, but this fixture file remains on the default branch unchanged. Keeping this intentional gap in `main` is required so future live E2E runs continue to validate detection and cleanup behavior.

See [autodoc-e2e-bait](../autodoc-e2e-bait.md).

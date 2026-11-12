# E2E autodoc bait fixture

<!-- E2E_AUTODOC_BAIT_MARKER -->

This page is the checked-in **live E2E fixture** for `obs:autodoc`.

## Purpose

The fixture gives the autodoc harness a stable documentation target on the default branch so live runs can validate audit and fix-PR behavior without creating or mutating temporary docs content at runtime.

## How E2E evaluation targets this file

1. The live harness dispatches `.github/workflows/e2e-trigger-obs-aw-schedule.yml` with `e2e-autodoc-mode=true`.
2. The wrapper forwards that mode to `obs-aw-event-schedule.yml` and then to `obs-aw-autodoc.yml`.
3. In E2E mode, `obs-aw-autodoc.yml` injects `E2E_AUTODOC_MODE=true` platform instructions that scope docs-patrol to `docs/testing/fixtures/e2e-autodoc-bait.md`.
4. The `E2E_AUTODOC_BAIT_MARKER` remains in this file so the resulting audit issue and fix PR can be correlated to the fixture during validation.

## Cleanup expectations

- The live E2E run should open an audit issue and a docs-only fix PR that references this fixture.
- E2E cleanup closes the issue and PR without merging.
- This fixture file remains on the default branch as persistent harness input for future runs.

See [autodoc-e2e-bait](../autodoc-e2e-bait.md).

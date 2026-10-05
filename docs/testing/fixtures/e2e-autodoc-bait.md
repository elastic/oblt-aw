# E2E autodoc bait fixture

<!-- E2E_AUTODOC_BAIT_MARKER -->

This page is the **live E2E fixture** for `obs:autodoc`.

## Purpose

This fixture gives the autodoc audit a deterministic, repository-owned markdown
target for end-to-end validation without creating or deleting documentation on
the default branch during runtime.

## How E2E mode evaluates this file

The live harness dispatches control-plane workflow
`e2e-trigger-obs-aw-schedule.yml` with input `e2e-autodoc-mode=true`. That
input flows into `obs-aw-autodoc`, which injects
`E2E_AUTODOC_MODE=true` audit instructions so docs-patrol evaluates **only**
`docs/testing/fixtures/e2e-autodoc-bait.md` and correlates findings with
`E2E_AUTODOC_BAIT_MARKER`.

## Cleanup expectations

After a live E2E run:

- The generated autodoc issue is closed during cleanup.
- Any fix PR opened for that issue is closed during cleanup.
- This fixture file remains checked in on the default branch and is not deleted
  by the harness.

See [autodoc-e2e-bait](../autodoc-e2e-bait.md).

# E2E autodoc bait fixture

<!-- E2E_AUTODOC_BAIT_MARKER -->

This page is the **live E2E fixture** for `obs:autodoc`.

## Purpose

The live harness uses this checked-in markdown file as a deterministic target so docs-patrol can detect a known documentation gap during E2E execution without creating or mutating default-branch content at runtime.

## Framework-only trigger and mode

In live E2E runs, `e2e-autodoc.yml` dispatches framework-only `e2e-trigger-obs-aw-schedule.yml` with `e2e-autodoc-mode=true`. That mode scopes docs-patrol evaluation to this fixture so the run can assert issue creation against this file path and marker (`E2E_AUTODOC_BAIT_MARKER`) without changing client schedule workflow behavior.

## Cleanup expectations

After the E2E assertions complete, the harness cleanup closes the issue and any linked fix PR opened for this fixture. The fixture file remains checked in on the default branch.

See [autodoc-e2e-bait](../autodoc-e2e-bait.md).

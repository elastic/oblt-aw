# E2E autodoc bait fixture page

<!-- E2E_AUTODOC_BAIT_MARKER -->

This page is the **live E2E fixture** for `obs:autodoc`.

## Status

Incomplete on purpose. Do **not** treat this as finished product documentation.

## Purpose

The live autodoc E2E harness needs a deterministic, checked-in documentation gap so docs-patrol can open a predictable audit issue without mutating `main` at runtime. This fixture provides that target and is identified by `E2E_AUTODOC_BAIT_MARKER`.

## How E2E evaluation is enabled

- The framework-only workflow `e2e-trigger-obs-aw-schedule.yml` is dispatched with `e2e-autodoc-mode=true`.
- In that mode, the wrapper injects fixed audit-only platform instructions (`E2E_AUTODOC_MODE=true`).
- Those instructions scope docs-patrol evaluation to this fixture path so the run validates issue creation behavior for a known docs gap.

## Cleanup expectations

- The E2E-generated audit issue and any follow-up fix PR are expected to be closed without merge after verification.
- This fixture file remains on the default branch so future live E2E runs can continue validating the same deterministic path.

See [autodoc-e2e-bait](../autodoc-e2e-bait.md).

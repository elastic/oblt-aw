# E2E autodoc bait fixture

<!-- E2E_AUTODOC_BAIT_MARKER -->

This page is the **live E2E fixture** for `obs:autodoc`.

## Status

Incomplete on purpose for the live autodoc E2E assertions. This page documents the fixture behavior, but it remains an intentional bait target and should not be merged as a product-doc completion.

## Harness purpose

The autodoc E2E harness needs a stable, checked-in documentation gap so audit and fix stages can be validated without mutating the default branch at runtime. This fixture provides that gap and marker for correlation in audit findings.

## How `e2e-autodoc-mode` evaluates this file

The framework-only dispatcher [`.github/workflows/e2e-trigger-obs-aw-schedule.yml`](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/e2e-trigger-obs-aw-schedule.yml) calls `obs-aw-event-schedule.yml` with `schedule-profile: daily` and forwards the `e2e-autodoc-mode` input. When `e2e-autodoc-mode=true`, `obs-aw-autodoc.yml` injects fixed audit instructions (`E2E_AUTODOC_MODE=true`) so docs-patrol evaluates **only** `docs/testing/fixtures/e2e-autodoc-bait.md`.

## Cleanup expectations

For live E2E runs, cleanup closes the generated audit issue and closes fix PRs that reference that issue. This fixture file remains on the default branch and is not deleted during cleanup.

See [autodoc-e2e-bait](../autodoc-e2e-bait.md) and [autodoc-e2e](../autodoc-e2e.md).

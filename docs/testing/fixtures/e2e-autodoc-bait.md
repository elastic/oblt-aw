# E2E autodoc bait fixture

<!-- E2E_AUTODOC_BAIT_MARKER -->

This page is the checked-in **live E2E fixture** for `obs:autodoc`.

## Purpose and audience

The fixture provides a stable, intentional docs gap that the live autodoc harness can target without mutating `main` at runtime. It is maintained for E2E validation by maintainers working on the autodoc audit/fix route, not as end-user product documentation.

## E2E trigger and mode behavior

During live E2E, `e2e-autodoc.yml` dispatches framework-only `e2e-trigger-obs-aw-schedule.yml` with `e2e-autodoc-mode=true`. That route forwards a boolean `e2e-autodoc-mode` input to `obs-aw-event-schedule.yml`, and `obs-aw-autodoc.yml` injects `E2E_AUTODOC_MODE=true` into audit instructions. In this mode, docs-patrol evaluates **only** `docs/testing/fixtures/e2e-autodoc-bait.md` and opens exactly one issue that cites this path and `E2E_AUTODOC_BAIT_MARKER`.

## Cleanup expectations

After the live run, cleanup closes the generated autodoc issue and closes only fix PRs that reference that issue; those PRs are not merged as part of E2E cleanup. The fixture file itself remains on the default branch and is re-checked on later runs.

See [autodoc-e2e-bait](../autodoc-e2e-bait.md).

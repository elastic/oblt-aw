# E2E autodoc bait fixture

<!-- E2E_AUTODOC_BAIT_MARKER -->

This page is the **live E2E fixture** for `obs:autodoc` and is intentionally
checked into the default branch so the harness can evaluate deterministic
documentation drift without creating or deleting docs at runtime.

## Status

Fixture content complete for the E2E assertions in
[`docs/testing/autodoc-e2e.md`](../autodoc-e2e.md) and
[`docs/testing/autodoc-e2e-bait.md`](../autodoc-e2e-bait.md).

## Purpose of the live autodoc E2E harness

The harness validates the full production autodoc route for `obs:autodoc`: audit
creates a documentation-drift issue, and fix creates a docs PR from that issue.
This fixture is the single controlled gap used for that validation path.

## How `e2e-trigger-obs-aw-schedule.yml` / `e2e-autodoc-mode` enables evaluation

Live E2E dispatches
[`e2e-trigger-obs-aw-schedule.yml`](../../../.github/workflows/e2e-trigger-obs-aw-schedule.yml)
with `e2e-autodoc-mode=true`. That input is forwarded into
[`obs-aw-event-schedule.yml`](../../../.github/workflows/obs-aw-event-schedule.yml)
and then into
[`obs-aw-autodoc.yml`](../../../.github/workflows/obs-aw-autodoc.yml),
where audit receives fixed platform instructions with `E2E_AUTODOC_MODE=true`.
In this mode, docs-patrol evaluates only this fixture path and correlates
findings by path + `E2E_AUTODOC_BAIT_MARKER`.

## Cleanup expectations

- The E2E run closes only the issue and PR created for this fixture.
- This fixture file remains on the default branch after cleanup.
- Harness success requires side-effect evidence that cleanup completed and the
  bait fixture is still present (`cleanup.bait_present`).

See [autodoc-e2e-bait](../autodoc-e2e-bait.md).

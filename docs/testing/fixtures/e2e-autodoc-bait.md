# E2E autodoc bait (intentional incomplete page)

<!-- E2E_AUTODOC_BAIT_MARKER -->

This page is the **live E2E fixture** for `obs:autodoc`.

## Status

Incomplete on purpose. Do **not** treat this as finished product documentation.

## Purpose

The live autodoc E2E harness needs one checked-in documentation page with an
intentional gap so the audit stage can detect drift and the fix stage can open
a docs PR against a real path. This fixture provides that stable target without
runtime writes to the default branch.

## Execution path

The live harness dispatches control-plane workflow
`.github/workflows/e2e-trigger-obs-aw-schedule.yml` with
`e2e-autodoc-mode=true`. That entrypoint passes the mode flag into
`obs-aw-event-schedule.yml`, which invokes `obs-aw-autodoc.yml` in E2E mode.

In E2E mode, the audit prompt receives `E2E_AUTODOC_MODE=true` and is scoped to
evaluate **only** `docs/testing/fixtures/e2e-autodoc-bait.md`. The expected
audit artifact is one issue that cites this path and includes
`E2E_AUTODOC_BAIT_MARKER`.

## Cleanup expectations

For live E2E cleanup:

- Close the generated issue after assertions are complete.
- Close any generated fix PR that references that issue (no merge).
- Keep this fixture file on the default branch so future E2E runs have the same
  deterministic bait input.

See [autodoc-e2e-bait](../autodoc-e2e-bait.md).

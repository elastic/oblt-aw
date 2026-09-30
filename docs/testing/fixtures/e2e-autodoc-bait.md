# E2E autodoc bait fixture

<!-- E2E_AUTODOC_BAIT_MARKER -->

This page is the **checked-in live E2E fixture** for `obs:autodoc`.

## Harness purpose

The live harness needs a stable, default-branch markdown target that docs-patrol can
evaluate without creating or deleting repository content at runtime. This fixture
provides that deterministic target and is correlated by path plus
`E2E_AUTODOC_BAIT_MARKER`.

## Mode and trigger behavior

Normal schedule/manual autodoc runs skip this path.

Live E2E dispatches control-plane `e2e-trigger-obs-aw-schedule.yml` with
`e2e-autodoc-mode=true`. That signal is forwarded into `obs-aw-autodoc`, which
injects fixed audit-only platform instructions containing `E2E_AUTODOC_MODE=true`.
In that mode, docs-patrol evaluates **only** this file and opens one issue that
cites this fixture path and `E2E_AUTODOC_BAIT_MARKER`.

## Cleanup expectations

After the live run, cleanup closes the issue opened for this fixture and closes any
fix PRs that reference that issue. The fixture file itself remains on the default
branch (no runtime mutation of checked-in docs).

See [autodoc-e2e-bait](../autodoc-e2e-bait.md) and [autodoc-e2e](../autodoc-e2e.md).

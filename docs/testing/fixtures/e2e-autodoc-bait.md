# E2E autodoc bait fixture

<!-- E2E_AUTODOC_BAIT_MARKER -->

This page is the **live E2E fixture** for `obs:autodoc`.

## Purpose of the live autodoc E2E harness

The autodoc E2E harness validates the end-to-end remediation loop for docs patrol:

1. schedule-triggered audit opens an autodoc issue for this fixture,
2. create-PR-from-issue updates the fixture docs,
3. the resulting PR is ready for human review.

This file intentionally remains in the repository so the live test always has a deterministic documentation target.

## How this file is selected in E2E mode

The control-plane workflow `.github/workflows/e2e-trigger-obs-aw-schedule.yml` dispatches schedule routing with `e2e-autodoc-mode=true`.

When that flag is enabled, the audit wrapper injects `E2E_AUTODOC_MODE=true`, and docs patrol is scoped to evaluate **only** `docs/testing/fixtures/e2e-autodoc-bait.md` for this run.

## Cleanup expectations

After a successful remediation cycle:

- the generated autodoc issue and remediation PR are closed/merged through normal workflow completion,
- this fixture file remains on the default branch as the persistent E2E bait source,
- the `E2E_AUTODOC_BAIT_MARKER` comment stays present for deterministic correlation and auditing.

See [autodoc-e2e-bait](../autodoc-e2e-bait.md) and [autodoc-e2e](../autodoc-e2e.md) for the full harness flow.

# E2E autodoc bait fixture

<!-- E2E_AUTODOC_BAIT_MARKER -->

This page is the checked-in **live E2E fixture** for `obs:autodoc`.

## Purpose

The autodoc E2E harness needs a stable, known markdown path that the audit stage can
target without creating or deleting docs on the default branch at runtime. This file
provides that fixture and keeps the marker token used to correlate the resulting audit
issue body.

## E2E mode selection and wiring

- The live harness dispatches control-plane `e2e-trigger-obs-aw-schedule.yml` with
  `e2e-autodoc-mode=true`.
- That input is forwarded into `obs-aw-autodoc`, where E2E-only
  `platform-additional-instructions` include `E2E_AUTODOC_MODE=true` and constrain
  docs-patrol to evaluate **only**
  `docs/testing/fixtures/e2e-autodoc-bait.md`.
- Normal schedule/manual production runs do not use this E2E mode and skip this path.

## Cleanup expectations

Live E2E cleanup closes the issue/PR artifacts created for the run, but this fixture
file remains on the default branch. Cleanup success includes evidence that the bait is
still present after cleanup (`bait_present`).

## Notes

Historically this page was "Incomplete on purpose" so docs-patrol could generate a
deterministic finding during E2E runs. Keep the marker and fixture role intact for
harness correlation.

See [autodoc-e2e-bait](../autodoc-e2e-bait.md) for broader harness context.

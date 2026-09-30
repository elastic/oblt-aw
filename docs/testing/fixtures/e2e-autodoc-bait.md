# E2E autodoc bait (intentional incomplete page)

<!-- E2E_AUTODOC_BAIT_MARKER -->

This page is the **live E2E fixture** for `obs:autodoc`.

## Status

Intentionally incomplete in production context. Do **not** treat this as
finished product documentation.

## Purpose

The live autodoc E2E harness validates that docs-patrol can detect a concrete,
known documentation gap and open a targeted issue that references this fixture
path and `E2E_AUTODOC_BAIT_MARKER`.

## How evaluation is triggered

During live E2E, `e2e-autodoc.yml` dispatches
`e2e-trigger-obs-aw-schedule.yml` with `e2e-autodoc-mode=true`. That route
invokes `obs-aw-autodoc` with fixed audit instructions
(`E2E_AUTODOC_MODE=true`) so docs-patrol evaluates only this fixture file.
Outside E2E mode, this file is skipped by normal docs-patrol runs.

## Cleanup expectations

Live E2E cleanup closes the issue/PR artifacts created during the test run.
This fixture file remains checked in on the default branch as persistent bait
for future E2E validations.

## Operator note

This page is intentionally incomplete by design and exists only as controlled
input for live autodoc E2E. Do not merge "completion" changes to this fixture
unless the test design itself is being changed.

See [autodoc-e2e-bait](../autodoc-e2e-bait.md).

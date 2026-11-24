# E2E autodoc bait (intentional incomplete page)

<!-- E2E_AUTODOC_BAIT_MARKER -->

This page is the **live E2E fixture** for `obs:autodoc`.

## Status

This file is a **fixture page** for live E2E verification, not product documentation.

## Harness purpose

The live autodoc E2E harness uses this page as a stable, known audit target so `obs:autodoc` can prove end-to-end issue creation behavior against a real repository file.

## How E2E evaluation is enabled

Framework-only `e2e-trigger-obs-aw-schedule.yml` runs with `e2e-autodoc-mode=true`. In that mode, the wrapper injects E2E audit context (`E2E_AUTODOC_MODE=true`) and scopes docs patrol evaluation to this fixture path.

## Cleanup expectations

After the E2E assertion, the generated issue/PR is closed without merge. This fixture file remains on the default branch so future live runs can assert the same behavior.

See [autodoc-e2e-bait](../autodoc-e2e-bait.md).

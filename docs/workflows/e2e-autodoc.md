# Workflow: `e2e-autodoc.yml`

## At a glance

| | |
| --- | --- |
| Platform | GitHub Actions |
| Source | [`.github/workflows/e2e-autodoc.yml`](../../.github/workflows/e2e-autodoc.yml) |
| Trigger | `workflow_dispatch` or `workflow_call` |

## Purpose

Runs a live end-to-end audit-and-fix test of `obs:autodoc` in this repository. The source describes the sequence: inspect the checked-in bait document, dispatch the control-plane schedule wrapper in bait-only mode, observe the audit issue and resulting fix PR, then close the issue and PR. It is not part of the default PR CI gate.

## Execution flow

The single `e2e` job validates manual `checkout-ref` input before checking out that ref, installs Python 3.14 dependencies from `requirements-runtime.txt`, runs `scripts/obs/e2e/autodoc_e2e_harness.py`, then evaluates its outcome with `oracle_autodoc_e2e.py` against `testdata/agentic/autodoc`. The harness step is allowed to return a nonzero status so the structured oracle can report the result. Failure summaries and JSON artifacts are uploaded even when a prior step fails.

The workflow uses the stable case ID `schedule-audit-fix-pr-live`, a 180-minute timeout, and non-cancelling concurrency.

## Inputs, outputs, and access

Optional `checkout-ref` defaults to `main`. No outputs or repository secrets are declared; the harness uses the workflow's `GITHUB_TOKEN`. The job can read contents and checks, and write issues and pull requests and dispatch Actions.

## Sources

- [E2E workflow](../../.github/workflows/e2e-autodoc.yml)
- [Harness](../../scripts/obs/e2e/autodoc_e2e_harness.py)
- [Oracle](../../scripts/obs/e2e/oracle_autodoc_e2e.py)
- [Autodoc route](obs-aw-autodoc.md)
- [Schedule dispatcher](e2e-trigger-obs-aw-schedule.md)
- [Test fixtures](../../testdata/agentic/autodoc/)

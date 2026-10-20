# Workflow: `e2e-estc-pr-buildkite-detective.yml`

## At a glance

| | |
| --- | --- |
| Platform | GitHub Actions |
| Source | [`.github/workflows/e2e-estc-pr-buildkite-detective.yml`](../../.github/workflows/e2e-estc-pr-buildkite-detective.yml) |
| Trigger | `workflow_dispatch` or `workflow_call` |

## Purpose

Verifies the live happy path for `obs:estc-pr-buildkite-detective`: a failing Buildkite build publishes a commit status, the status route runs the detective, and the PR receives the resulting analysis. The workflow reuses a long-lived fixture PR and does not close it.

## Execution flow

The `e2e` job validates manual `checkout-ref`, installs Python 3.14 dependencies, runs `estc_pr_buildkite_detective_e2e_harness.py`, and checks the outcome with `oracle_estc_pr_buildkite_detective_e2e.py` using `testdata/agentic/estc-pr-buildkite-detective`. The case ID is `status-failure-open-pr-live`; concurrent runs are serialized and not cancelled.

The job uploads outcome/oracle artifacts after printing a failure summary. It relies on the separate checked-in Buildkite fixture pipeline to generate the intentional failed status; the harness does not synthesize the successful-path status.

## Inputs, outputs, and access

Optional `checkout-ref` defaults to `main`. The job declares `BUILDKITE_TOKEN`, `E2E_BUILDKITE_ORG`, and `E2E_BUILDKITE_PIPELINE` by name. The variable defaults are `elastic` and `oblt-aw-e2e-estc-fail`. The job can write contents, pull requests, and issues; read statuses, Actions, and checks. The workflow call inherits secrets from its caller.

## Sources

- [E2E workflow](../../.github/workflows/e2e-estc-pr-buildkite-detective.yml)
- [Harness](../../scripts/obs/e2e/estc_pr_buildkite_detective_e2e_harness.py)
- [Oracle](../../scripts/obs/e2e/oracle_estc_pr_buildkite_detective_e2e.py)
- [Buildkite failure pipeline](../../.buildkite/pipeline.e2e-estc-fail.yml)
- [Buildkite pipeline notes](../../.buildkite/README.e2e-estc-fail.md)
- [Status event route](obs-aw-event-status.md)
- [Test fixtures](../../testdata/agentic/estc-pr-buildkite-detective/)

# Workflow: `e2e-pr-actions-detective.yml`

## At a glance

| | |
| --- | --- |
| Platform | GitHub Actions |
| Source | [`.github/workflows/e2e-pr-actions-detective.yml`](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/e2e-pr-actions-detective.yml) |
| Trigger | `workflow_dispatch` or `workflow_call` |

## Purpose

Verifies the live `obs:pr-actions-detective` path from an intentional failed Actions run through the `workflow_run` event to the detective's PR comment. It reuses a long-lived fixture PR and does not close it.

## Execution flow

The `e2e` job validates a manually supplied `checkout-ref`, resolves a Vault token policy from `config/e2e.json` or `config/release.json`, creates an ephemeral Vault-app token, installs Python 3.14 dependencies, runs `pr_actions_detective_e2e_harness.py`, and validates the result with `oracle_pr_actions_detective_e2e.py` against `testdata/agentic/pr-actions-detective`. It prints a structured failure summary and uploads artifacts for 30 days.

The stable case ID is `workflow-run-failure-open-pr-live`. A non-cancelling concurrency group serializes use of the shared fixture. Vault-app authorship is used so fixture `pull_request` events can fire without the GitHub Actions bot approval gate.

## Inputs, outputs, and access

Optional `checkout-ref` defaults to `main`. The job can write contents, pull requests, and issues; read Actions and checks; and request OIDC. No long-lived secret is declared; the workflow creates an ephemeral token from the configured token policy.

## Sources

- [E2E workflow](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/e2e-pr-actions-detective.yml)
- [Harness](https://github.com/elastic/oblt-aw/blob/main/scripts/obs/e2e/pr_actions_detective_e2e_harness.py)
- [Oracle](https://github.com/elastic/oblt-aw/blob/main/scripts/obs/e2e/oracle_pr_actions_detective_e2e.py)
- [Intentional-failure workflow](e2e-pr-actions-detective-fail.md)
- [Workflow-run event route](obs-aw-event-workflow-run.md)
- [Test fixtures](https://github.com/elastic/oblt-aw/tree/main/testdata/agentic/pr-actions-detective)

# Workflow: `e2e-repo-scheduled.yml`

## At a glance

| | |
| --- | --- |
| Platform | GitHub Actions |
| Source | [`.github/workflows/e2e-repo-scheduled.yml`](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/e2e-repo-scheduled.yml) |
| Trigger | `workflow_dispatch` or `workflow_call` |

## Purpose

Runs a live end-to-end test of `obs:repo-scheduled` in this repository. The harness checks the checked-in bait instruction, dispatches the control-plane schedule wrapper, and for the issue case waits for the agent leaf and marker issue, then closes the issue. It is not part of the default PR CI gate. The control plane does not keep a permanent root `apm.yml` for the bait; E2E mode injects the checked-in bait file during discovery.

## Execution flow

The `e2e` job matrix covers `schedule-issue-live` and `schedule-noop-live`. It validates manual `checkout-ref` input before checking out that ref, installs Python 3.14 dependencies from `requirements-runtime.txt`, runs `scripts/obs/e2e/repo_scheduled_e2e_harness.py`, then evaluates its outcome with `oracle_repo_scheduled_e2e.py` against `testdata/agentic/repo-scheduled`. The harness step may return nonzero so the structured oracle can report the result. Failure summaries and JSON artifacts are uploaded even when a prior step fails. If the correlated schedule run completes without a required agent leaf, the harness fails closed instead of polling until timeout.

The workflow uses a 180-minute timeout and non-cancelling concurrency (`e2e-repo-scheduled`).

## Inputs, outputs, and access

Optional `checkout-ref` defaults to `main`. No outputs or repository secrets are declared; the harness uses the workflow's `GITHUB_TOKEN`. The job can read contents and checks, write issues and pull requests, and dispatch Actions.

## Sources

- [E2E workflow](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/e2e-repo-scheduled.yml)
- [Harness](https://github.com/elastic/oblt-aw/blob/main/scripts/obs/e2e/repo_scheduled_e2e_harness.py)
- [Oracle](https://github.com/elastic/oblt-aw/blob/main/scripts/obs/e2e/oracle_repo_scheduled_e2e.py)
- [Repo scheduled route](obs-aw-repo-scheduled.md)
- [Schedule dispatcher](e2e-trigger-obs-aw-schedule.md)
- [Test fixtures](https://github.com/elastic/oblt-aw/tree/main/testdata/agentic/repo-scheduled)
- [Harness notes](../testing/repo-scheduled-e2e.md)

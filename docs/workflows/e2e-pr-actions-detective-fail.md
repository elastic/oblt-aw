# Workflow: `e2e-pr-actions-detective-fail.yml`

## At a glance

| | |
| --- | --- |
| Platform | GitHub Actions |
| Source | [`.github/workflows/e2e-pr-actions-detective-fail.yml`](../../.github/workflows/e2e-pr-actions-detective-fail.yml) |
| Trigger | Pull request events: `opened`, `synchronize`, `reopened`, and `labeled`; path-filtered to the E2E bait file |

## Purpose

Produces a deliberate failed Actions run for the PR Actions Detective live E2E. The failure is a test signal, not a product regression.

## Execution flow

The `intentional-fail` job runs only for same-repository pull requests with label `e2e:pr-actions-detective` and head branch `e2e/pr-actions-detective`. The path filter watches only `testdata/agentic/pr-actions-detective/e2e-fail-trigger.md`; the source comment explains this prevents seeding the workflow file itself from triggering a second failure on a different commit. The job prints a stable marker and exits with status 1.

## Inputs, outputs, and access

No inputs, outputs, or secrets are declared. The workflow requests only `contents: read`; the job runs on `ubuntu-slim` with a five-minute timeout.

## Sources

- [Intentional-failure workflow](../../.github/workflows/e2e-pr-actions-detective-fail.yml)
- [PR Actions Detective E2E](e2e-pr-actions-detective.md)
- [Fixture data](../../testdata/agentic/pr-actions-detective/)

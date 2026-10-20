# Workflow: `e2e-dependency-review.yml`

## At a glance

| | |
| --- | --- |
| Platform | GitHub Actions |
| Source | [`.github/workflows/e2e-dependency-review.yml`](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/e2e-dependency-review.yml) |
| Trigger | `workflow_dispatch` or `workflow_call` |

## Purpose

Runs the live `obs:dependency-review` path using an ephemeral Actions pin-bump pull request. The expected result is dependency-review analysis, an analysis comment, and merge-ready state; the E2E does not wait for automerge. It is not part of the default PR CI gate.

## Execution flow

The `e2e` job validates manual `checkout-ref`, resolves a Vault token policy from `config/e2e.json` or `config/release.json`, creates an ephemeral GitHub token, installs Python 3.14 dependencies, runs `dependency_review_e2e_harness.py`, and evaluates the outcome using `oracle_dependency_review_e2e.py` and `testdata/agentic/dependency-review`. It emits a failure summary and uploads artifacts with 30-day retention.

The workflow serializes runs under `e2e-dependency-review` without cancelling an active run and uses the case ID `actions-pin-bump-live`.

## Inputs, outputs, and access

Optional `checkout-ref` defaults to `main`. The job requests content and pull-request writes, Actions/check reads, issue writes, and OIDC. No repository secret is declared by this workflow; it uses the ephemeral token created from the configured workflow token policy.

## Sources

- [E2E workflow](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/e2e-dependency-review.yml)
- [Harness](https://github.com/elastic/oblt-aw/blob/main/scripts/obs/e2e/dependency_review_e2e_harness.py)
- [Oracle](https://github.com/elastic/oblt-aw/blob/main/scripts/obs/e2e/oracle_dependency_review_e2e.py)
- [Fixture workflow](e2e-dependency-review-actions-fixture.md)
- [Dependency-review route](obs-aw-dependency-review.md)
- [Test fixtures](https://github.com/elastic/oblt-aw/tree/main/testdata/agentic/dependency-review)

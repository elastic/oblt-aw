# Workflow: `e2e-automerge-all-files.yml`

## At a glance

| | |
| --- | --- |
| Platform | GitHub Actions |
| Source | [`.github/workflows/e2e-automerge-all-files.yml`](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/e2e-automerge-all-files.yml) |
| Trigger | `workflow_dispatch` or `workflow_call` |

## Purpose

Exercises the live `obs:automerge:all-files` route with consumer `apm.yml` custom
trigger labels on a stacked temporary base. Matrix cases cover the happy path
(custom label → approve → merge) and the negative path (label absent → no
automerge). It is not a default PR CI gate.

## Execution flow

Each matrix job validates a manual `checkout-ref`, resolves the Vault token
policy from `config/e2e.json` for direct E2E dispatch or `config/release.json`
when called from release promotion, then obtains an ephemeral Vault-app token.
It installs Python 3.14 dependencies, runs `automerge_all_files_e2e_harness.py`,
and checks the structured result with `oracle_automerge_all_files_e2e.py` against
`testdata/agentic/automerge-all-files`. Failure summaries and artifacts are
retained for 30 days.

## Inputs, outputs, and access

Optional `checkout-ref` defaults to `main`. The job requests content and
pull-request writes, Actions and checks reads, issue writes, and OIDC. No
long-lived secret is declared; token-policy configuration is read from the
checked-out JSON files.

## Sources

- [E2E workflow](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/e2e-automerge-all-files.yml)
- [Harness](https://github.com/elastic/oblt-aw/blob/main/scripts/obs/e2e/automerge_all_files_e2e_harness.py)
- [Oracle](https://github.com/elastic/oblt-aw/blob/main/scripts/obs/e2e/oracle_automerge_all_files_e2e.py)
- [Automerge route](obs-aw-automerge.md)
- [Test fixtures](https://github.com/elastic/oblt-aw/tree/main/testdata/agentic/automerge-all-files)
- [Harness doc](../testing/automerge-all-files-e2e.md)

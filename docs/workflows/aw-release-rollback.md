# Workflow: `aw-release-rollback.yml`

## Overview

Source file: [.github/workflows/aw-release-rollback.yml](../../.github/workflows/aw-release-rollback.yml)

Quick rollback: must run on the default branch. Retargets the current production major (`tags.current`, e.g. `v0` today, later `vN`) to `previous`, pushes rollback tags, then lands `config/release-pointers.json` via the same Vault PR path as promote (org rules block direct pushes to `main`; prepare leaves uncommitted pointer edits on the default-branch tip so `create-pull-request` can own `release/rollback-pointers-<run_id>`; fail closed if tip’s pointer file moved since the plan-base SHA or if the PR head moves after `create-pull-request`). Confirm input must be exactly `rollback`. Uses `rollback-workflow-token-policy` from [`config/release.json`](../../config/release.json) (see [agentic-release-model](../operations/agentic-release-model.md#vault-token-policy-pointers-pr)).

Recovery target: ≤ 15 minutes when tags/pointers are healthy. Full runbook: [agentic-release-model](../operations/agentic-release-model.md).

## Inputs

| Input | Required | Purpose |
|-------|----------|---------|
| `confirm` | yes | Must be `rollback` |
| `dry-run` | no | Plan only |

## References

- Promote: [aw-release-promote](aw-release-promote.md)

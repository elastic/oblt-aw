# Workflow: `aw-release-rollback.yml`

## Overview

Source file: [.github/workflows/aw-release-rollback.yml](../../.github/workflows/aw-release-rollback.yml)

Quick rollback: must run on the default branch. Retargets the current production major (`tags.current`, e.g. `v0` today, later `vN`) to `previous` and lands `config/release-pointers.json` via the same Vault PR path as promote (org rules block direct pushes to `main`). Confirm input must be exactly `rollback`. Requires the release Vault token policy to allow `aw-release-rollback.yml` (see [agentic-release-model](../operations/agentic-release-model.md#vault-token-policy-pointers-pr)).

Recovery target: ≤ 15 minutes when tags/pointers are healthy. Full runbook: [agentic-release-model](../operations/agentic-release-model.md).

## Inputs

| Input | Required | Purpose |
|-------|----------|---------|
| `confirm` | yes | Must be `rollback` |
| `dry-run` | no | Plan only |

## References

- Promote: [aw-release-promote](aw-release-promote.md)

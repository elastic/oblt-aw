# Workflow: `aw-release-rollback.yml`

## Overview

Source file: [.github/workflows/aw-release-rollback.yml](../../.github/workflows/aw-release-rollback.yml)

Quick rollback: must run on the default branch. Retargets the current production major (`tags.current`, e.g. `v0` today, later `vN`) to `previous` and updates `config/release-pointers.json`. Confirm input must be exactly `rollback`.

Recovery target: ≤ 15 minutes when tags/pointers are healthy. Full runbook: [agentic-release-model](../operations/agentic-release-model.md).

## Inputs

| Input | Required | Purpose |
|-------|----------|---------|
| `confirm` | yes | Must be `rollback` |
| `dry-run` | no | Plan only |

## References

- Promote: [aw-release-promote](aw-release-promote.md)

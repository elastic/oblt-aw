# Workflow: `aw-release-rollback.yml`

## Overview

Source file: [.github/workflows/aw-release-rollback.yml](../../.github/workflows/aw-release-rollback.yml)

Quick rollback: retargets the current production major (`v0` today, later `vN`) to `previous-prod` and updates `config/release-pointers.json`. Confirm input must be exactly `rollback`.

Recovery target: ≤ 15 minutes when tags/pointers are healthy. Full runbook: [agentic-release-model](../operations/agentic-release-model.md).

## Inputs

| Input | Required | Purpose |
|-------|----------|---------|
| `confirm` | yes | Must be `rollback` |
| `dry-run` | no | Plan only |

## References

- Promote: [aw-release-promote](aw-release-promote.md)

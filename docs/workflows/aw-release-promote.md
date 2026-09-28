# Workflow: `aw-release-promote.yml`

## Overview

Source file: [.github/workflows/aw-release-promote.yml](../../.github/workflows/aw-release-promote.yml)

Promotes the tip of the default branch (`main`) to the moving major tag after `e2e-all` passes. Pins E2E checkout to `github.sha` at promote start. Computes the next semver from `release-type`, updates `config/release-pointers.json`, and pushes release tags.

Full model and runbook: [agentic-release-model](../operations/agentic-release-model.md).

## Inputs

| Input | Required | Purpose |
|-------|----------|---------|
| `release-type` | yes | `patch`, `minor`, or `major` (first promote → `v1.0.0`) |
| `dry-run` | no | Run E2E and plan only |

## References

- Rollback: [aw-release-rollback](aw-release-rollback.md)
- E2E orchestrator: [.github/workflows/e2e-all.yml](../../.github/workflows/e2e-all.yml)

# Workflow: `aw-release-promote.yml`

## Overview

Source file: [.github/workflows/aw-release-promote.yml](../../.github/workflows/aw-release-promote.yml)

Promotes the tip of the default branch (`main`) after `e2e-all` passes. Pins E2E harness checkout to `github.sha` at promote start; aborts if `main` advanced before tagging. Commits `config/release-pointers.json` before pushing tags (immutable semver without force; moving tags with force).

Full model and runbook: [agentic-release-model](../operations/agentic-release-model.md).

## Inputs

| Input | Required | Purpose |
|-------|----------|---------|
| `release-type` | yes | `patch`, `minor`, or `major` (first promote → `v0.0.0`) |
| `dry-run` | no | Run E2E and plan only |

## References

- Rollback: [aw-release-rollback](aw-release-rollback.md)
- E2E orchestrator: [.github/workflows/e2e-all.yml](../../.github/workflows/e2e-all.yml)

# Workflow: `aw-release-promote.yml`

## Overview

Source file: [.github/workflows/aw-release-promote.yml](../../.github/workflows/aw-release-promote.yml)

Promotes a candidate SHA to the moving major tag (`v1`) after **gating** E2E summaries pass. Updates `config/release-pointers.json` and pushes release tags.

Full model and runbook: [agentic-release-model](../operations/agentic-release-model.md).

## Inputs

| Input | Required | Purpose |
|-------|----------|---------|
| `candidate-sha` | yes | Full SHA to promote |
| `semver` | yes | Immutable tag (e.g. `v1.0.0`) |
| `e2e-run-id` | yes | Actions run that uploaded leaf `summary.json` artifacts |
| `bootstrap` | no | First promote only |
| `dry-run` | no | Plan only |

## References

- Rollback: [aw-release-rollback](aw-release-rollback.md)
- E2E orchestrator: [.github/workflows/e2e-all.yml](../../.github/workflows/e2e-all.yml)

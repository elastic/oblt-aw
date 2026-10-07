# Workflow: `aw-release-promote.yml`

## Overview

Source file: [.github/workflows/aw-release-promote.yml](../../.github/workflows/aw-release-promote.yml)

Promotes the tip of the default branch (`main`) after `e2e-all` passes. Pins E2E harness checkout to `github.sha` at promote start. If `main` advanced during E2E, tagging still proceeds for the gated SHA. Pushes release tags, then lands `config/release-pointers.json` via a Vault-authored PR (org rules block direct pushes to `main`). Prepare leaves uncommitted pointer edits on the default-branch tip so `create-pull-request` can own `release/pointers-<run_id>`; the job fails closed if tip’s pointer file moved since the plan-base SHA or if the PR head moves after `create-pull-request`. Then creates a GitHub Release with auto-generated notes for the immutable semver tag. Tags are published before the pointers merge so distribute cannot pin production installs at a missing `@vN`. Re-dispatch is safe when the immutable tag already points at the planned SHA: promote skips recreating and re-pushing that tag and continues with pointers.

Full model and runbook: [agentic-release-model](../operations/agentic-release-model.md).

## Inputs

| Input | Required | Purpose |
|-------|----------|---------|
| `release-type` | yes | `patch`, `minor`, or `major` (first promote → `v0.0.0`) |
| `dry-run` | no | Run E2E and plan only |

## References

- Rollback: [aw-release-rollback](aw-release-rollback.md)
- E2E orchestrator: [.github/workflows/e2e-all.yml](../../.github/workflows/e2e-all.yml)

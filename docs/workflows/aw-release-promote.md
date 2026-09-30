# Workflow: `aw-release-promote.yml`

## Overview

Source file: [.github/workflows/aw-release-promote.yml](../../.github/workflows/aw-release-promote.yml)

Promotes a SHA on the default branch (`main`) after `e2e-all` passes. Pins E2E harness checkout to the promote SHA (dispatch tip, or optional `promote-sha`). If `main` advanced during E2E, tagging still proceeds for the gated SHA; the pointers commit is rebased onto current `main`. Creates a GitHub Release with auto-generated notes for the immutable semver tag.

Full model and runbook: [agentic-release-model](../operations/agentic-release-model.md).

## Inputs

| Input | Required | Purpose |
|-------|----------|---------|
| `release-type` | yes | `patch`, `minor`, or `major` (first promote → `v0.0.0`) |
| `promote-sha` | no | Full SHA to promote (default = tip at dispatch; must be on default-branch history) |
| `dry-run` | no | Run E2E and plan only |

## References

- Rollback: [aw-release-rollback](aw-release-rollback.md)
- E2E orchestrator: [.github/workflows/e2e-all.yml](../../.github/workflows/e2e-all.yml)

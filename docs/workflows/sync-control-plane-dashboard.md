# Sync Control Plane Dashboard Workflow

## Overview

Source file: [.github/workflows/sync-control-plane-dashboard.yml](../../.github/workflows/sync-control-plane-dashboard.yml)

This workflow creates or updates the Control Plane Dashboard issue in each repository listed in [active-repositories.json](../../active-repositories.json). The dashboard lists all available agentic workflows with maturity badges and opt-in checkboxes.

## Prerequisites

- [workflow-registry.json](../../workflow-registry.json) — workflow metadata (id, name, description, maturity)
- [active-repositories.json](../../active-repositories.json) — target repositories
- Token policy configured for [elastic/oblt-actions/github/create-token@v1](https://github.com/elastic/oblt-actions/blob/v1/github/create-token/action.yml)

## Usage

Triggers:

- `push` to `main` when any of these paths change:
  - [workflow-registry.json](../../workflow-registry.json)
  - [active-repositories.json](../../active-repositories.json)
  - [.github/workflows/sync-control-plane-dashboard.yml](../../.github/workflows/sync-control-plane-dashboard.yml)
- `workflow_dispatch`

*Note: Editing the dashboard issue does not trigger this workflow. Dashboard opt-in/opt-out is read at runtime by the ingress (`get-enabled-workflows`); there is no `issues.edited` trigger.*

Execution:

1. **prepare-repos job:** Builds repos matrix from [active-repositories.json](../../active-repositories.json) via [scripts/build_repos_matrix.py](../../scripts/build_repos_matrix.py); outputs JSON for matrix strategy
2. **sync-dashboard job:** Matrix job (one job per repo); each invokes `scripts/sync_control_plane_dashboard.py --repo <owner/repo>`:
   - Search for existing open issue with label `oblt-aw/dashboard`
   - Create or update the issue with title `[oblt-aw] Control Plane Dashboard`, body from registry (header, maturity badges, checkboxes, descriptions)
   - Pin the issue via `gh issue pin` (if limit of 3 pins reached, log and continue)

## Configuration

Permissions:

- `contents: read`
- Job: `id-token: write`, `contents: read`

Concurrency:

- group: `sync-control-plane-dashboard`
- `cancel-in-progress: false`

## References

- [docs/operations/control-plane-dashboard.md](../operations/control-plane-dashboard.md) — user instructions
- [docs/operations/control-plane-dashboard-format.md](../operations/control-plane-dashboard-format.md) — dashboard issue format
- [Issue #3732 comment (implementation plan)](https://github.com/elastic/observability-robots/issues/3732#issuecomment-4054356635)

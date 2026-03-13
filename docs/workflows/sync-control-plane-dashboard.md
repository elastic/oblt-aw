# Sync Control Plane Dashboard Workflow

## Overview

Source file: `.github/workflows/sync-control-plane-dashboard.yml`

This workflow creates or updates the Control Plane Dashboard issue in each repository listed in `active-repositories.json`. The dashboard lists all available agentic workflows with maturity badges and opt-in checkboxes.

## Prerequisites

- `workflow-registry.json` — workflow metadata (id, name, description, maturity)
- `active-repositories.json` — target repositories
- Token policy configured for `elastic/oblt-actions/github/create-token@v1`

## Usage

Triggers:

- `push` to `main` when any of these paths change:
  - `workflow-registry.json`
  - `active-repositories.json`
  - `.github/workflows/sync-control-plane-dashboard.yml`
- `schedule` (daily, e.g. 06:00 UTC)
- `workflow_dispatch`

Execution:

1. For each repository in `active-repositories.json`:
   - Search for existing open issue with label `oblt-aw/dashboard`
   - Create or update the issue with title `[OBLT AW] Control Plane Dashboard`, body from registry (header, maturity badges, checkboxes, descriptions)
   - Pin the issue when possible (up to 3 pins per repo; if limit reached, log and continue)

## Configuration

Permissions:

- `contents: read`
- Job: `id-token: write`, `contents: read`

Concurrency:

- group: `sync-control-plane-dashboard`
- `cancel-in-progress: false`

## References

- `docs/operations/control-plane-dashboard.md` — user instructions
- `docs/operations/control-plane-dashboard-format.md` — dashboard issue format
- `docs/plans/issue-3732-control-plane-dashboard.md` — implementation plan

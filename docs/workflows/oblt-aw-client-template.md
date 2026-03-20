# Workflow: Client Template `oblt-aw.yml`

## Overview

Source files:

- `.github/remote-workflow-template/oblt-aw.yml`
- `.github/workflows/oblt-aw.yml`

This workflow is the client-facing entrypoint template distributed to target repositories.

## Usage

Triggers:

- `schedule` (`0 6 * * *`)
- `workflow_dispatch`
- `issues` (`opened`, `labeled`)
- `pull_request` (`opened`, `synchronize`, `reopened`)
- `pull_request_review` (`submitted`)

Execution flow:

1. **check-dashboard job** (runs first, in target repo with default `GITHUB_TOKEN`): Looks up an open issue labeled `oblt-aw/dashboard`. If none exists, outputs an empty `enabled_workflows` string (ingress enables all workflows). If it exists, parses checkboxes (`^- [x] <!-- oblt-aw:workflow-id -->` at line start in the Enable/Disable list) and outputs `enabled_workflows` as a JSON array string: `[]` when nothing is checked, or `["id", ...]` for checked workflows only. Permissions: `issues: read`.
2. **run-aw job** (`needs: check-dashboard`): Passes `enabled_workflows` to the ingress; calls `elastic/oblt-aw/.github/workflows/oblt-aw-ingress.yml@main`

## Configuration

Top-level permissions:

- `actions: read`

Job-level permissions:

- `actions: read`
- `checks: read`
- `contents: write`
- `discussions: write`
- `issues: write`
- `pull-requests: write`

Required secret mapping:

- `COPILOT_GITHUB_TOKEN: ${{ secrets.COPILOT_GITHUB_TOKEN }}`

## References

- Distribution process: `docs/operations/distribute-client-workflow.md`
- Ingress doc: `docs/workflows/oblt-aw-ingress.md`

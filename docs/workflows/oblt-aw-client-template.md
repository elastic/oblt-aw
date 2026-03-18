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

1. **check-dashboard job** (runs first, in target repo with default `GITHUB_TOKEN`): Fetches the Control Plane Dashboard issue via API, parses checkboxes (`☑ <!-- oblt-aw:workflow-id -->`), outputs `enabled_workflows` as JSON array. Permissions: `issues: read`. Behavior: no dashboard → all workflows; dashboard with all unchecked → none; dashboard with some checked → only those.
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

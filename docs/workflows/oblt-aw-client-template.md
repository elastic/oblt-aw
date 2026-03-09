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

Delegation:

- job `run-aw` calls `elastic/oblt-aw/.github/workflows/oblt-aw-ingress.yml@main`

## Configuration

Top-level permissions:

- `actions: read`

Job-level permissions:

- `actions: read`
- `contents: write`
- `discussions: write`
- `issues: write`
- `pull-requests: write`

Required secret mapping:

- `COPILOT_GITHUB_TOKEN: ${{ secrets.COPILOT_GITHUB_TOKEN }}`

## References

- Distribution process: `docs/operations/distribute-client-workflow.md`
- Ingress doc: `docs/workflows/oblt-aw-ingress.md`

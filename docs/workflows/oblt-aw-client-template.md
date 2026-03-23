# Workflow: Client Template `oblt-aw.yml`

## Overview

**Source of truth (edit here only):** `.github/remote-workflow-template/oblt-aw.yml`

**Do not edit** `.github/workflows/oblt-aw.yml` in this repository. That path is not maintained as a hand-edited copy of the template; avoid changing it in PRs and automation. `distribute-client-workflow` installs the **remote template** into **other** repositories as their `.github/workflows/oblt-aw.yml`.

This workflow is the client-facing entrypoint template distributed to target repositories.

## Usage

Triggers:

- `schedule` (`0 6 * * *`)
- `workflow_dispatch`
- `issues` (`opened`, `labeled`)
- `pull_request` (`opened`, `synchronize`, `reopened`)
- `pull_request_review` (`submitted`)

Execution flow:

1. **run-aw job** calls `elastic/oblt-aw/.github/workflows/oblt-aw-ingress.yml@main`. The ingress runs `get_enabled_workflows` first (in the consumer repo context): it looks up an open issue labeled `oblt-aw/dashboard`, parses checkboxes (`^- [x] <!-- oblt-aw:workflow-id -->` at line start in the Enable/Disable list), and derives normalized `enabled_workflows` (always `[]` or `["id", ...]`). Use `EFFECTIVE_RAW`: empty means no dashboard issue → all workflows enabled; otherwise `[]` or `["id", ...]` from the issue. Consumers do not need to call `get_enabled_workflows` separately; the ingress invokes it.

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

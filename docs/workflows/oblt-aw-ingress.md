# Workflow: `oblt-aw-ingress.yml`

## Overview

Source file: `.github/workflows/oblt-aw-ingress.yml`

This is the reusable orchestration entrypoint for `oblt-aw`. It routes to specialized workflows based on event context.

## Prerequisites

- Called by consumer workflows using `workflow_call`.
- Optional secret: `COPILOT_GITHUB_TOKEN`.

## Usage

Supported triggers in this workflow file:

- `schedule`
- `workflow_call`
- `issues` with `opened` and `labeled`
- `pull_request` with `opened`, `synchronize`, `reopened`

Routing jobs:

- `dependency-review`
- `resource-not-accessible-by-integration-detector`, `resource-not-accessible-by-integration-triage`, `resource-not-accessible-by-integration-fixer` (unified `enabled_workflow`: `resource-not-accessible-by-integration`)
- `unsupported-trigger`

Each workflow job is gated by the `enabled_workflows` input (from the client's `check-dashboard` job). Semantics: empty string (no dashboard) → all workflows enabled; empty array `[]` (dashboard exists, all unchecked) → none enabled; non-empty array → only listed workflows run.

## Configuration

Top-level permissions:

- `actions: read`
- `contents: write`
- `discussions: write`
- `issues: write`
- `pull-requests: write`

## API / Interface

Interface exposed through `workflow_call`:

- Input: `enabled_workflows` (JSON array of workflow IDs; from client's `check-dashboard` job; empty string = all enabled, `[]` = none, non-empty = only listed)
- Secret: `COPILOT_GITHUB_TOKEN` (`required: false`)

## Examples

Minimal consumer reference (client template has `check-dashboard` job that outputs `enabled_workflows`):

```yaml
jobs:
  run-aw:
    needs: check-dashboard
    uses: elastic/oblt-aw/.github/workflows/oblt-aw-ingress.yml@main
    with:
      enabled_workflows: ${{ needs.check-dashboard.outputs.enabled_workflows }}
    secrets:
      COPILOT_GITHUB_TOKEN: ${{ secrets.COPILOT_GITHUB_TOKEN }}
```

## References

- `docs/routing/README.md`

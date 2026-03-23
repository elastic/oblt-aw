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
- `workflow_dispatch` (top-level entrypoint manual runs; used by duplicate-issue-detector routing)
- `issues` with `opened` and `labeled`
- `pull_request` with `opened`, `synchronize`, `reopened`
- `pull_request_review` with `submitted`

Routing jobs:

- `dependency-review`
- `duplicate-issue-detector` (`enabled_workflow` id: `duplicate-issue-detector`; runs on `issues: opened` or `workflow_dispatch`)
- `issue-triage` (`enabled_workflow` id: `issue-triage`; runs on `issues: opened`)
- `resource-not-accessible-by-integration-detector`, `resource-not-accessible-by-integration-triage`, `resource-not-accessible-by-integration-fixer` (unified `enabled_workflow`: `resource-not-accessible-by-integration`)
- `unsupported-trigger`

Each workflow job is gated by the `enabled_workflows` input (from the client's `check-dashboard` job). Accepted formats only: empty string (no open dashboard issue) → all workflows enabled; JSON array string `[]` (dashboard exists, nothing checked) → no workflows; `["id",...]` → only listed workflows run. Bare workflow IDs are not accepted.

## Configuration

Top-level permissions:

- `actions: read`
- `contents: write`
- `discussions: write`
- `issues: write`
- `pull-requests: write`

## API / Interface

Interface exposed through `workflow_call`:

- Input: `enabled_workflows` (string; `''` = no dashboard → all enabled; `[]` = dashboard present, none checked → none; `["id"]` / `["a","b"]` = only those IDs. Bare workflow IDs are not accepted; use delimiter format in callers.)
- Secret: `COPILOT_GITHUB_TOKEN` (`required: false`)

## Examples

Minimal consumer reference (client template has `check-dashboard` job that outputs `enabled_workflows` as `''` or a JSON array string):

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

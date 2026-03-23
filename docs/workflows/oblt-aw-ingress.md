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

The ingress runs `get_enabled_workflows.yml` first. Gating uses `EFFECTIVE_RAW` and `enabled_workflows`: `EFFECTIVE_RAW` empty (no open dashboard issue) → all workflows enabled; `EFFECTIVE_RAW` non-empty and normalized array `[]` → no workflows; non-empty array with IDs → only listed workflows run. Bare workflow IDs are not accepted.

## Configuration

Top-level permissions:

- `actions: read`
- `contents: write`
- `discussions: write`
- `issues: write`
- `pull-requests: write`

## API / Interface

Interface exposed through `workflow_call`:

- Secret: `COPILOT_GITHUB_TOKEN` (`required: false`)

## Examples

Minimal consumer reference (client template calls ingress only; dashboard read runs inside ingress):

```yaml
jobs:
  run-aw:
    uses: elastic/oblt-aw/.github/workflows/oblt-aw-ingress.yml@main
    secrets:
      COPILOT_GITHUB_TOKEN: ${{ secrets.COPILOT_GITHUB_TOKEN }}
```

## References

- `docs/routing/README.md`

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
- `workflow_dispatch`
- `workflow_call`
- `issues` with `opened` and `labeled`
- `pull_request` with `opened`, `synchronize`, `reopened`

Routing jobs:

- `dependency-review`
- `resource-not-accessible-by-integration-detector`
- `security-detector`
- `resource-not-accessible-by-integration-triage`
- `resource-not-accessible-by-integration-fixer`
- `unsupported-trigger`

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

Minimal consumer reference:

```yaml
jobs:
  run-aw:
    uses: elastic/oblt-aw/.github/workflows/oblt-aw-ingress.yml@main
    secrets:
      COPILOT_GITHUB_TOKEN: ${{ secrets.COPILOT_GITHUB_TOKEN }}
```

## References

- `docs/routing/README.md`

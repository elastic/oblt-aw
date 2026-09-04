# Workflow: `obs-aw-resource-not-accessible-by-integration-detector.yml`

## Overview

Source file: [.github/workflows/obs-aw-resource-not-accessible-by-integration-detector.yml](../../.github/workflows/obs-aw-resource-not-accessible-by-integration-detector.yml)

This reusable workflow detects `Resource not accessible by integration` occurrences in workflow logs and creates issue output through the log-searching-agent workflow. It discovers all workflows in the repository and runs the agent per workflow via a matrix strategy.

When the agent creates an issue for findings, its instructions require adding the label `oblt-aw/detector/res-not-accessible-by-integration` so ingress can route the issue to the triage workflow.

## Prerequisites

- Triggered via `workflow_call`.
- Nested lock uses optional `GH_AW_GITHUB_TOKEN` / MCP secrets only (same pattern as other `ai-github-actions` agentic locks). Copilot runs with `github.token`; no repository `COPILOT_GITHUB_TOKEN` secret is required.

## Usage

The workflow uses two jobs:

1. **discover** — Lists all workflow numeric IDs via the GitHub API (avoids 404 when the API expects exact workflow file names).
2. **search** — Matrix job that calls `obs-aw-log-searching-agent` per workflow:
   - [elastic/ai-github-actions/.github/workflows/gh-aw-log-searching-agent.lock.yml@fix/log-searching-agent-copilot-token-align](https://github.com/elastic/ai-github-actions/blob/fix/log-searching-agent-copilot-token-align/.github/workflows/gh-aw-log-searching-agent.lock.yml)

The detector is invoked by ingress only on scheduled runs (`github.event_name == schedule`). Ingress `workflow_dispatch` does not route this detector job.

Configured parameters:

- **Lookback**: 1 day (aligned with daily schedule trigger)
- **Search term**: `Resource not accessible by integration`
- **Conclusion filter**: `any` (success, failure, cancelled)
- **Issue title prefix**: `[oblt-aw][resource-not-accessible-by-integration]`

## Configuration

Permissions:

- `actions: read`
- `contents: read`
- `issues: write`
- `copilot-requests: write`

## API / Interface

`workflow_call` contract:


## References

- Routing rules: [docs/routing/resource-not-accessible-by-integration-routing.md](../routing/resource-not-accessible-by-integration-routing.md)
- Log-searching-agent proposal: [elastic/ai-github-actions#548](https://github.com/elastic/ai-github-actions/pull/548#issuecomment-3997493806)

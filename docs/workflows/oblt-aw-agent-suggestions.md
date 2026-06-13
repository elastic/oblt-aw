# Workflow: `oblt-aw-agent-suggestions.yml`

## Overview

Source file: [.github/workflows/oblt-aw-agent-suggestions.yml](../../.github/workflows/oblt-aw-agent-suggestions.yml)

This reusable wrapper runs the upstream agent-suggestions workflow with repository-specific policy for issue creation.

## Prerequisites

- Triggered via `workflow_call`.
- Called by the schedule event orchestrator (`oblt-aw-event-schedule.yml`) after [aw-prelude.yml](aw-prelude.md) computes shared gating and allow-list inputs.
- Required secret: `COPILOT_GITHUB_TOKEN`.

## Usage

This wrapper runs two jobs in sequence:

- `resolve-apm-assets`: calls [aw-resolve-apm-assets.yml](aw-resolve-apm-assets.md) to resolve platform/APM prompt assets before invoking the upstream lock workflow. This job requires `id-token: write`.
- `agent-suggestions`: delegates to the upstream lock workflow and passes `additional-instructions` from `resolve-apm-assets`.

- [elastic/ai-github-actions/.github/workflows/gh-aw-agent-suggestions.lock.yml@main](https://github.com/elastic/ai-github-actions/blob/main/.github/workflows/gh-aw-agent-suggestions.lock.yml)

Repository-specific instructions enforce:

- no issue creation when there are no net-new recommendations
- label `agentic-workflow` on created report issues
- expiration window `24h` for created report issues
- detailed analysis per recommendation (pain points, gaps, benefits, trade-offs)

## Configuration

Permissions:

- Workflow-level: `contents: read`
- `resolve-apm-assets` job: `contents: read`, `id-token: write`
- `agent-suggestions` job: `contents: read`, `issues: write`, `pull-requests: read`

## API / Interface

`workflow_call` contract:

- Input: `shared-proceed` (`required: true`, `type: string`)
- Input: `shared-allowed-pr-authors-json` (`required: true`, `type: string`)
- Input: `shared-allowed-pr-authors-csv` (`required: true`, `type: string`)
- Input: `shared-allowed-issue-authors-json` (`required: true`, `type: string`)
- Input: `shared-allowed-issue-authors-csv` (`required: true`, `type: string`)
- Input: `shared-token-policy` (`required: true`, `type: string`)
- Secret: `COPILOT_GITHUB_TOKEN` (`required: true`)

## References

- Routing rules: [docs/routing/agent-suggestions-routing.md](../routing/agent-suggestions-routing.md)

# Workflow: `gh-aw-agent-suggestions.yml`

## Overview

Source file: [.github/workflows/gh-aw-agent-suggestions.yml](../../.github/workflows/gh-aw-agent-suggestions.yml)

This reusable wrapper runs the upstream agent-suggestions workflow with repository-specific policy for issue creation.

## Prerequisites

- Triggered via `workflow_call`.
- Required secret: `COPILOT_GITHUB_TOKEN`.

## Usage

The job `run` delegates to:

- [elastic/ai-github-actions/.github/workflows/gh-aw-agent-suggestions.lock.yml@main](https://github.com/elastic/ai-github-actions/blob/main/.github/workflows/gh-aw-agent-suggestions.lock.yml)

Repository-specific instructions enforce:

- no issue creation when there are no net-new recommendations
- label `agentic-workflow` on created report issues
- expiration window `24h` for created report issues
- detailed analysis per recommendation (pain points, gaps, benefits, trade-offs)

## Configuration

Permissions:

- `actions: read`
- `contents: read`
- `issues: write`
- `pull-requests: read`

## API / Interface

`workflow_call` contract:

- Secret: `COPILOT_GITHUB_TOKEN` (`required: true`)

## References

- Routing notes: [.github/workflow-routing/agent-suggestions/README.md](../../.github/workflow-routing/agent-suggestions/README.md)

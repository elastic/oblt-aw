# Workflow: `oblt-aw-agent-suggestions.yml`

## Overview

Source file: [.github/workflows/oblt-aw-agent-suggestions.yml](../../.github/workflows/oblt-aw-agent-suggestions.yml)

This reusable wrapper runs the upstream agent-suggestions workflow with repository-specific policy for issue creation.

## Prerequisites

- Triggered via `workflow_call`.

## Usage

The job `agent-suggestions` delegates to:

- [elastic/ai-github-actions/.github/workflows/gh-aw-agent-suggestions.lock.yml@main](https://github.com/elastic/ai-github-actions/blob/main/.github/workflows/gh-aw-agent-suggestions.lock.yml)

Repository-specific instructions enforce:

- no issue creation when there are no net-new recommendations
- label `agentic-workflow` on created report issues
- automatic issue expiration via upstream safe-outputs (`expires: 7d` in `gh-aw-agent-suggestions.lock.yml`); do not pass `expires` or custom issue `fields` from agent output
- detailed analysis per recommendation (pain points, gaps, benefits, trade-offs)

## Configuration

Permissions:

- `actions: read`
- `contents: read`
- `issues: write`
- `pull-requests: read`

## API / Interface

`workflow_call` contract:


## References

- Routing rules: [docs/routing/agent-suggestions-routing.md](../routing/agent-suggestions-routing.md)

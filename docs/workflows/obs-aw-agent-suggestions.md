# Workflow: `obs-aw-agent-suggestions.yml`

## Overview

Source file: [.github/workflows/obs-aw-agent-suggestions.yml](../../.github/workflows/obs-aw-agent-suggestions.yml)

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

The wrapper sets `report-failure-as-issue: false` on the lock workflow call so runtime/tooling failures stay in the Actions run instead of opening `[aw] ...` meta-issues; intentional findings from normal safe-output actions are unchanged.

## Configuration

Permissions:

- `actions: read`
- `contents: read`
- `issues: write`
- `pull-requests: read`

## API / Interface

`workflow_call` contract:

- `shared-proceed` (`required: true`, string) — prelude gate; jobs run only when this is `'true'`.
- `shared-allowed-pr-authors-json` (`required: true`, string) — PR author allowlist JSON from prelude.
- `shared-allowed-pr-authors-csv` (`required: true`, string) — PR author allowlist CSV from prelude.
- `shared-allowed-issue-authors-json` (`required: true`, string) — issue author allowlist JSON from prelude.
- `shared-allowed-issue-authors-csv` (`required: true`, string) — issue author allowlist CSV from prelude.
- `shared-token-policy` (`required: true`, string) — token policy identifier passed from prelude for workflows that need ephemeral token minting.


## References

- Routing rules: [docs/routing/agent-suggestions-routing.md](../routing/agent-suggestions-routing.md)

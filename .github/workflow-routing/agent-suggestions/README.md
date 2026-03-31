# Agent suggestions routing

This folder documents routing and conventions for agent workflow suggestion reporting.

## Entrypoint route

`oblt-aw-ingress.yml` dispatches to `gh-aw-agent-suggestions.yml` when:

- event is `schedule` or `workflow_dispatch`

## Behavior extensions

The agent suggestions workflow adds repository-specific instructions to:

- call `noop` and avoid issue creation when no net-new recommendations are found
- add label `agentic-workflow` to created report issues
- set report issue expiration to `24h` and auto-close after that period
- include detailed analysis and implementation benefits for each recommendation

## Upstream reusable workflow

The wrapper delegates to:

- [elastic/ai-github-actions/.github/workflows/gh-aw-agent-suggestions.lock.yml@main](https://github.com/elastic/ai-github-actions/blob/main/.github/workflows/gh-aw-agent-suggestions.lock.yml)

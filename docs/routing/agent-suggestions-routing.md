# Agent Suggestions Routing

## Overview

Entrypoint source: `.github/workflows/oblt-aw-ingress.yml`

Routed workflow source: `.github/workflows/gh-aw-agent-suggestions.yml`

## Usage

Ingress routes to agent suggestions when:

- `github.event_name == 'schedule'`
- The Control Plane dashboard gate allows registry id `agent-suggestions` (see `docs/workflows/oblt-aw-ingress.md` — `get-enabled-workflows` / `enabled-workflows`)

The event name is evaluated in the context of the workflow run that invoked the ingress (`workflow_call`).

## Behavior extensions

The agent suggestions workflow adds repository-specific instructions to:

- call `noop` and avoid issue creation when no net-new recommendations are found
- add label `agentic-workflow` to created report issues
- set report issue expiration to `24h` and auto-close after that period
- include detailed analysis and implementation benefits for each recommendation

## Upstream reusable workflow

The wrapper delegates to:

- `elastic/ai-github-actions/.github/workflows/gh-aw-agent-suggestions.lock.yml@main`

## References

- `docs/workflows/gh-aw-agent-suggestions.md`

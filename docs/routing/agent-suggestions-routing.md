# Agent Suggestions Routing

## Overview

Client template: `trigger-obs-aw-agent-suggestions.yml` → `obs-aw-agent-suggestions.yml`

Routed workflow source: `.github/workflows/obs-aw-agent-suggestions.yml`

## Usage

Ingress routes to agent suggestions when:

- `github.event_name == 'schedule'`
- The Control Plane dashboard gate allows registry id `agent-suggestions` (see `docs/workflows/aw-prelude.md` — `get-enabled-workflows` / `enabled-workflows`)

The event name is evaluated in the context of the workflow run that invoked the ingress (`workflow_call`).

## Behavior extensions

The agent suggestions workflow adds repository-specific instructions to:

- call `noop` and avoid issue creation when no net-new recommendations are found
- add label `agentic-workflow` to created report issues
- rely on upstream safe-outputs expiration (`expires: 7d`); do not pass `expires` or custom issue `fields` from agent output
- include detailed analysis and implementation benefits for each recommendation

## Upstream reusable workflow

The wrapper delegates to:

- `elastic/ai-github-actions/.github/workflows/gh-aw-agent-suggestions.lock.yml@main`

## References

- `docs/workflows/obs-aw-agent-suggestions.md`

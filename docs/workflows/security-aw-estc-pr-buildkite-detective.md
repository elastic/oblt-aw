# Workflow: `security-aw-estc-pr-buildkite-detective.yml`

## Overview

Source file: [.github/workflows/security-aw-estc-pr-buildkite-detective.yml](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/security-aw-estc-pr-buildkite-detective.yml)

Reusable wrapper for the Security org route of PR Buildkite Detective. It calls the same in-repo lock as the Observability route ([obs-aw-estc-pr-buildkite-detective.md](obs-aw-estc-pr-buildkite-detective.md)). The client template `trigger-security-aw-status.yml` sends failed Buildkite `status` events to `security-aw-event-status.yml`. That orchestrator calls this wrapper when the prelude allows `security:estc-pr-buildkite-detective`.

## Prerequisites

- The wrapper runs through `workflow_call` from `security-aw-event-status.yml`, which the client `trigger-security-aw-status.yml` calls.
- Required secret: `BUILDKITE_API_TOKEN`. The client template maps it from the repository secret `BUILDKITE_LOGS_API_TOKEN`. The token needs read access to build logs in the Buildkite organization of the repository.

## Usage

The orchestrator routes here when all of these conditions are true:

- `github.event_name == 'status'`.
- `github.event.state == 'failure'`.
- `github.event.context` contains `buildkite`.
- The Control Plane dashboard gate passes for registry id `estc-pr-buildkite-detective` (`enabled-workflows` contains `security:estc-pr-buildkite-detective`).

The wrapper has three jobs:

1. `check-pr` looks for an open pull request that contains the commit.
2. `resolve-apm-assets` calls `aw-resolve-agentic-assets.yml`.
3. `estc-pr-buildkite-detective` calls `./.github/workflows/gh-aw-estc-pr-buildkite-detective.lock.yml`.

Edit the agent behavior in the shared source `.github/workflows/gh-aw-estc-pr-buildkite-detective.md`. Run `make compile-aw-check` after each change. The Observability and Security routes share this lock.

## Configuration

Top-level permission: `contents: read`.

| Job | Permissions |
|-----|-------------|
| `check-pr` | `pull-requests: read` |
| `resolve-apm-assets` | `contents: read`, `id-token: write` |
| `estc-pr-buildkite-detective` | `actions: read`, `contents: read`, `issues: write`, `pull-requests: write`, `copilot-requests: write` |

## API / Interface

`workflow_call` contract:

- Input: `shared-proceed` (`required: true`)
- Secret: `BUILDKITE_API_TOKEN` (`required: true`)

## References

- Client template: [security-aw-client-template.md](security-aw-client-template.md) — registry id `estc-pr-buildkite-detective`
- Observability route: [obs-aw-estc-pr-buildkite-detective.md](obs-aw-estc-pr-buildkite-detective.md)

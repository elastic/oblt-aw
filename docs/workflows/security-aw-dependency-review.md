# Workflow: `security-aw-dependency-review.yml`

## Overview

Source file: [.github/workflows/security-aw-dependency-review.yml](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/security-aw-dependency-review.yml)

Reusable wrapper for the Security org route of Dependency Review. It calls the same in-repo lock as the Observability route ([obs-aw-dependency-review.md](obs-aw-dependency-review.md)). The client template `trigger-security-aw-pull-request.yml` sends `pull_request` events to `security-aw-event-pull-request.yml`. That orchestrator calls this wrapper when the prelude allows `security:dependency-review`.

## Prerequisites

- The wrapper runs through `workflow_call` from `security-aw-event-pull-request.yml`, which the client `trigger-security-aw-pull-request.yml` calls.
- The route condition uses the allowed PR author list in [config/obs/allowed_pr_authors.json](https://github.com/elastic/oblt-aw/blob/main/config/obs/allowed_pr_authors.json). The Security org shares this list. The bot actors that the lock accepts are hardcoded to the same list in the GH-AW source.

## Usage

The orchestrator routes here when all of these conditions are true:

- `github.event_name == 'pull_request'`.
- The action is `opened`, `synchronize` or `reopened`.
- The author is on the allowed PR authors list.
- The Control Plane dashboard gate passes for registry id `dependency-review` (`enabled-workflows` contains `security:dependency-review`).

The wrapper has three jobs:

1. `resolve-apm-assets` calls `aw-resolve-agentic-assets.yml`.
2. `dependency-review` calls `./.github/workflows/gh-aw-dependency-review.lock.yml`.
3. `notify-no-comment` posts or updates a PR comment when the review posted no analysis.

Edit the agent behavior in the shared source `.github/workflows/gh-aw-dependency-review.md`. Run `make compile-aw-check` after each change. The Observability and Security routes share this lock.

## Configuration

Top-level permission: `contents: read`.

| Job | Permissions |
|-----|-------------|
| `resolve-apm-assets` | `contents: read`, `id-token: write` |
| `dependency-review` | `actions: read`, `contents: read`, `issues: write`, `pull-requests: write`, `copilot-requests: write`, `id-token: write` |
| `notify-no-comment` | `pull-requests: write` |

## API / Interface

`workflow_call` contract:

- Input: `shared-proceed` (`required: true`)
- Input: `shared-token-policy` (`required: true`)

## References

- Client template: [security-aw-client-template.md](security-aw-client-template.md) — registry id `dependency-review`
- Observability route: [obs-aw-dependency-review.md](obs-aw-dependency-review.md)

# Workflow: `obs-aw-duplicate-issue-detector.yml`

## Overview

Source file: [.github/workflows/obs-aw-duplicate-issue-detector.yml](../../.github/workflows/obs-aw-duplicate-issue-detector.yml)

Reusable wrapper that calls the locked duplicate-issue-detector workflow in [elastic/ai-github-actions](https://github.com/elastic/ai-github-actions). The client template `trigger-obs-aw-duplicate-issue-detector.yml` calls this workflow on `issues` `opened` or `workflow_dispatch` when prelude allows `obs:duplicate-issue-detector`.

## Prerequisites

- Triggered via `workflow_call` from `trigger-obs-aw-duplicate-issue-detector.yml` client templates.

## Usage

Ingress routes here when:

- `github.event_name == 'issues'` and `github.event.action == 'opened'`, or `github.event_name == 'workflow_dispatch'`, and
- Dashboard gate passes for registry id `duplicate-issue-detector` (`enabled-workflows` contains `obs:duplicate-issue-detector`).

The job `duplicate-issue-detector` calls:

- [elastic/ai-github-actions/.github/workflows/gh-aw-duplicate-issue-detector.lock.yml@main](https://github.com/elastic/ai-github-actions/blob/main/.github/workflows/gh-aw-duplicate-issue-detector.lock.yml)

Behavior and agent instructions for the locked workflow are defined in [elastic/ai-github-actions](https://github.com/elastic/ai-github-actions).

## Configuration

Permissions (job-level on the control-plane reusable; union mirrored on the client trigger):

| Job | Permissions |
|-----|-------------|
| `run-aw-prelude` | `contents: read`, `issues: read` |
| `duplicate-issue-detector` | `actions: read`, `contents: read`, `discussions: write`, `issues: write`, `pull-requests: read`, `copilot-requests: write` (matches `gh-aw-duplicate-issue-detector.lock.yml`) |

## API / Interface

`workflow_call` contract:


## References

- Client template: [obs-aw-client-template.md](obs-aw-client-template.md) — registry id `duplicate-issue-detector`
- Upstream lock: [elastic/ai-github-actions](https://github.com/elastic/ai-github-actions) — [`.github/workflows/gh-aw-duplicate-issue-detector.lock.yml`](https://github.com/elastic/ai-github-actions/blob/main/.github/workflows/gh-aw-duplicate-issue-detector.lock.yml)

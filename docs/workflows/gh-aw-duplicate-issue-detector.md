# Workflow: `gh-aw-duplicate-issue-detector.yml`

## Overview

Source file: [.github/workflows/gh-aw-duplicate-issue-detector.yml](../../.github/workflows/gh-aw-duplicate-issue-detector.yml)

Reusable wrapper that calls the locked duplicate-issue-detector workflow in [elastic/ai-github-actions](https://github.com/elastic/ai-github-actions). The client entrypoint (`oblt-aw` template) invokes `oblt-aw-ingress`, which runs this job when an issue is opened or when the entrypoint is manually dispatched, provided the workflow is enabled on the control-plane dashboard.

## Prerequisites

- Triggered via `workflow_call` from `oblt-aw-ingress.yml`.
- Required secret: `COPILOT_GITHUB_TOKEN`.

## Usage

Ingress routes here when:

- `github.event_name == 'issues'` and `github.event.action == 'opened'`, or `github.event_name == 'workflow_dispatch'`, and
- Dashboard gating allows `duplicate-issue-detector` (or no dashboard issue is present, so all workflows are enabled).

The job `run` calls:

- [elastic/ai-github-actions/.github/workflows/gh-aw-duplicate-issue-detector.lock.yml@main](https://github.com/elastic/ai-github-actions/blob/main/.github/workflows/gh-aw-duplicate-issue-detector.lock.yml)

Behavior and agent instructions for the locked workflow are defined in [elastic/ai-github-actions](https://github.com/elastic/ai-github-actions).

## Configuration

Permissions:

- `contents: read`
- `discussions: write`
- `issues: write`
- `pull-requests: read`

## API / Interface

`workflow_call` contract:

- Secret: `COPILOT_GITHUB_TOKEN` (`required: true`)

## References

- Ingress routing: [docs/workflows/oblt-aw-ingress.md](oblt-aw-ingress.md) — workflow id `duplicate-issue-detector` in [workflow-registry.json](../../config/obs/workflow-registry.json)
- Upstream lock: [elastic/ai-github-actions](https://github.com/elastic/ai-github-actions) — [`.github/workflows/gh-aw-duplicate-issue-detector.lock.yml`](https://github.com/elastic/ai-github-actions/blob/main/.github/workflows/gh-aw-duplicate-issue-detector.lock.yml)

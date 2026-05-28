# Workflow: `oblt-aw-issue-triage.yml`

## Overview

Source file: [.github/workflows/oblt-aw-issue-triage.yml](../../.github/workflows/oblt-aw-issue-triage.yml)

Reusable wrapper that calls the locked generic issue-triage workflow in [elastic/ai-github-actions](https://github.com/elastic/ai-github-actions). The client template `trigger-oblt-aw-issue-triage.yml` calls this workflow on `issues` `opened` when prelude allows `obs:issue-triage`.

## Prerequisites

- Triggered via `workflow_call` from `trigger-oblt-aw-issue-triage.yml` client templates.
- Required secret: `COPILOT_GITHUB_TOKEN`.

## Usage

Ingress routes here when:

- `github.event_name == 'issues'` and `github.event.action == 'opened'`, and
- Dashboard gating allows `issue-triage` (or no dashboard issue is present, so all workflows are enabled).

The job `issue-triage` calls:

- [elastic/ai-github-actions/.github/workflows/gh-aw-issue-triage.lock.yml@main](https://github.com/elastic/ai-github-actions/blob/main/.github/workflows/gh-aw-issue-triage.lock.yml)

Behavior and agent instructions for the locked workflow are defined in [elastic/ai-github-actions](https://github.com/elastic/ai-github-actions).

## Configuration

Permissions:

- `actions: read`
- `contents: read`
- `discussions: write`
- `issues: write`
- `pull-requests: write`

## API / Interface

`workflow_call` contract:

- Secret: `COPILOT_GITHUB_TOKEN` (`required: true`)

Ingress does not pass `allowed-bot-users` for this generic path; the upstream lock workflow uses its built-in defaults (no control-plane issue author list).

## References

- Client template: [oblt-aw-client-template.md](oblt-aw-client-template.md) — registry id `issue-triage`
- Specialized triage (Resource Not Accessible by Integration): [docs/workflows/oblt-aw-resource-not-accessible-by-integration-triage.md](oblt-aw-resource-not-accessible-by-integration-triage.md)
- Upstream lock: [elastic/ai-github-actions](https://github.com/elastic/ai-github-actions) — [`.github/workflows/gh-aw-issue-triage.lock.yml`](https://github.com/elastic/ai-github-actions/blob/main/.github/workflows/gh-aw-issue-triage.lock.yml)

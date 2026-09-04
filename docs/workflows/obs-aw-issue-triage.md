# Workflow: `obs-aw-issue-triage.yml`

## Overview

Source file: [.github/workflows/obs-aw-issue-triage.yml](../../.github/workflows/obs-aw-issue-triage.yml)

Reusable wrapper that calls the locked generic issue-triage workflow in [elastic/ai-github-actions](https://github.com/elastic/ai-github-actions). The client template `trigger-obs-aw-issue-triage.yml` calls this workflow on `issues` `opened` when prelude allows `obs:issue-triage`.

## Prerequisites

- Triggered via `workflow_call` from `trigger-obs-aw-issue-triage.yml` client templates.

## Usage

Ingress routes here when:

- `github.event_name == 'issues'` and `github.event.action == 'opened'`, and
- the issue does **not** carry specialized detector or triage labels:
  - `oblt-aw/detector/security`
  - `oblt-aw/detector/res-not-accessible-by-integration`
  - `oblt-aw/triage/security-*`
  - `oblt-aw/triage/res-not-accessible-by-integration`, and
- Dashboard gate passes for registry id `issue-triage` (`enabled-workflows` contains `obs:issue-triage`).

Those exclusions keep specialized security and resource-not-accessible triage authoritative when their detector or triage labels are present.

The job `issue-triage` calls:

- [elastic/ai-github-actions/.github/workflows/gh-aw-issue-triage.lock.yml@main](https://github.com/elastic/ai-github-actions/blob/main/.github/workflows/gh-aw-issue-triage.lock.yml)

Behavior and agent instructions for the locked workflow are defined in [elastic/ai-github-actions](https://github.com/elastic/ai-github-actions). The nested lock workflow mints an OIDC ephemeral token when `github-token-policy` is non-empty so label writes re-trigger downstream routes.

## Configuration

Permissions:

- `actions: read`
- `contents: read`
- `discussions: write`
- `issues: write`
- `pull-requests: write`
- `id-token: write`

## API / Interface

`workflow_call` contract:


Ingress does not pass `allowed-bot-users` for this generic path; the upstream lock workflow uses its built-in defaults (no control-plane issue author list).

## References

- Client template: [obs-aw-client-template.md](obs-aw-client-template.md) — registry id `issue-triage`
- Specialized triage (Resource Not Accessible by Integration): [docs/workflows/obs-aw-resource-not-accessible-by-integration-triage.md](obs-aw-resource-not-accessible-by-integration-triage.md)
- Upstream lock: [elastic/ai-github-actions](https://github.com/elastic/ai-github-actions) — [`.github/workflows/gh-aw-issue-triage.lock.yml`](https://github.com/elastic/ai-github-actions/blob/main/.github/workflows/gh-aw-issue-triage.lock.yml)

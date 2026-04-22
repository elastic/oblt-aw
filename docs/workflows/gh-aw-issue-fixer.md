# Workflow: `gh-aw-issue-fixer.yml`

## Overview

Source file: [.github/workflows/gh-aw-issue-fixer.yml](../../.github/workflows/gh-aw-issue-fixer.yml)

Reusable wrapper that calls the locked generic issue-fixer workflow in [elastic/ai-github-actions](https://github.com/elastic/ai-github-actions). The client entrypoint (`oblt-aw` template) invokes `oblt-aw-ingress`, which runs this job when an issue is labeled `oblt-aw/ai/fix-ready` and no specialized fixer flow applies.

## Prerequisites

- Triggered via `workflow_call` from `oblt-aw-ingress.yml`.
- Issue label must include `oblt-aw/ai/fix-ready`.
- Issue must not include specialized triage labels:
  - `oblt-aw/triage/security-*`
  - `oblt-aw/triage/res-not-accessible-by-integration`

## Usage

Ingress routes here when:

- `github.event_name == 'issues'` and `github.event.action == 'labeled'`, and
- `github.event.label.name == 'oblt-aw/ai/fix-ready'`, and
- issue labels do not match the specialized security or resource-not-accessible fixer routes, and
- dashboard gating allows `issue-fixer` (or no dashboard issue is present, so all workflows are enabled).

The job `run` calls:

- [elastic/ai-github-actions/.github/workflows/gh-aw-issue-fixer.lock.yml@main](https://github.com/elastic/ai-github-actions/blob/main/.github/workflows/gh-aw-issue-fixer.lock.yml)

Configured instructions require:

- strict execution of triage-generated plan
- draft PR first, then ready-for-review after validation
- reviewer request to [elastic/observablt-ci](https://github.com/orgs/elastic/teams/observablt-ci)
- no auto-merge

## Configuration

Permissions:

- `actions: read`
- `contents: write`
- `discussions: write`
- `issues: write`
- `pull-requests: write`

## API / Interface

`workflow_call` contract:

- No inputs.

## References

- Ingress routing: [docs/workflows/oblt-aw-ingress.md](oblt-aw-ingress.md) — workflow id `issue-fixer` in [workflow-registry.json](../../config/obs/workflow-registry.json)
- Routing rules: [docs/routing/issue-fixer-routing.md](../routing/issue-fixer-routing.md)
- Upstream lock: [elastic/ai-github-actions](https://github.com/elastic/ai-github-actions) — [`.github/workflows/gh-aw-issue-fixer.lock.yml`](https://github.com/elastic/ai-github-actions/blob/main/.github/workflows/gh-aw-issue-fixer.lock.yml)

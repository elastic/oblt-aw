# Workflow: `gh-aw-issue-fixer.yml`

## Overview

Source file: [.github/workflows/gh-aw-issue-fixer.yml](../../.github/workflows/gh-aw-issue-fixer.yml)

Reusable wrapper that calls the locked generic issue-fixer workflow in [elastic/ai-github-actions](https://github.com/elastic/ai-github-actions). The client entrypoint (`oblt-aw` template) invokes `oblt-aw-ingress`, which runs this job when an issue comment starts with `/ai implement`, the commenter is an org collaborator (`OWNER`, `MEMBER`, or `COLLABORATOR`), and no specialized fixer flow applies.

## Prerequisites

- Triggered via `workflow_call` from `oblt-aw-ingress.yml`.
- Triggering issue comment must start with `/ai implement` (for example, `/ai implement` or `/ai implement this`).
- Triggering comment author association must be one of: `OWNER`, `MEMBER`, `COLLABORATOR`.
- Issue must not include specialized triage labels:
  - `oblt-aw/triage/security-*`
  - `oblt-aw/triage/res-not-accessible-by-integration`

## Usage

Ingress routes here when:

- `github.event_name == 'issue_comment'` and `github.event.action == 'created'`, and
- comment is on an issue (not a PR), and
- `startsWith(github.event.comment.body, '/ai implement')`, and
- `github.event.comment.author_association` is `OWNER`, `MEMBER`, or `COLLABORATOR`, and
- issue labels do not match the specialized security or resource-not-accessible fixer routes, and
- dashboard gating allows `obs:issue-fixer` (or no dashboard issue is present, so all workflows are enabled).

The job `run` calls:

- [elastic/ai-github-actions/.github/workflows/gh-aw-issue-fixer.lock.yml@main](https://github.com/elastic/ai-github-actions/blob/main/.github/workflows/gh-aw-issue-fixer.lock.yml)

Configured instructions require:

- strict execution of the issue's triage-generated resolution plan as the source of truth
- draft PR first, then ready-for-review after validation
- reviewer request to [elastic/observablt-ci](https://github.com/orgs/elastic/teams/observablt-ci)
- no auto-merge

## Configuration

Permissions:

- top-level: `actions: read`
- job `run`: `contents: write`, `discussions: write`, `issues: write`, `pull-requests: write`
- job `request-reviewers`: `pull-requests: write`

## API / Interface

`workflow_call` contract:

- No inputs.
- No declared secrets.

## References

- Ingress routing: [docs/workflows/oblt-aw-ingress.md](oblt-aw-ingress.md) — workflow id `issue-fixer` (dashboard gate `obs:issue-fixer`) in [workflow-registry.json](../../config/obs/workflow-registry.json)
- Routing rules: [docs/routing/issue-fixer-routing.md](../routing/issue-fixer-routing.md)
- Upstream lock: [elastic/ai-github-actions](https://github.com/elastic/ai-github-actions) — [`.github/workflows/gh-aw-issue-fixer.lock.yml`](https://github.com/elastic/ai-github-actions/blob/main/.github/workflows/gh-aw-issue-fixer.lock.yml)

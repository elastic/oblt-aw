# Workflow: `obs-aw-issue-fixer.yml`

## Overview

Source file: [.github/workflows/obs-aw-issue-fixer.yml](../../.github/workflows/obs-aw-issue-fixer.yml)

Reusable wrapper that calls the locked generic issue-fixer workflow in [elastic/ai-github-actions](https://github.com/elastic/ai-github-actions). The client template `trigger-obs-aw-issue-fixer.yml` calls this workflow on `issue_comment` when prelude allows `obs:issue-fixer` and route guards pass.

## Prerequisites

- Triggered via `workflow_call` from `trigger-obs-aw-issue-fixer.yml` client templates.
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
- Dashboard gate passes for registry id `issue-fixer` (`enabled-workflows` contains `obs:issue-fixer`).

The job `run` calls:

- [elastic/ai-github-actions/.github/workflows/gh-aw-issue-fixer.lock.yml@main](https://github.com/elastic/ai-github-actions/blob/main/.github/workflows/gh-aw-issue-fixer.lock.yml)

Configured instructions require:

- strict execution of the issue's triage-generated resolution plan as the source of truth
- draft PR first, then ready-for-review after validation
- reviewer request to [elastic/observablt-ci](https://github.com/orgs/elastic/teams/observablt-ci)
- no auto-merge

The nested lock workflow mints an OIDC ephemeral token when `github-token-policy` is non-empty so pull requests and comments re-trigger downstream routes.

Workflow-specific prompt text lives in `platform-additional-instructions` on this wrapper. Shared draft, review, and merge policy is composed from control-plane fragments mapped under `workflows.issue-fixer` in [`config/obs/instruction-fragment-map.json`](../../config/obs/instruction-fragment-map.json) (see [instruction fragments](../architecture/instruction-fragments.md)).

## Configuration

Permissions:

- top-level: `contents: read`
- job `run`: `actions: read`, `contents: write`, `discussions: write`, `issues: write`, `pull-requests: write`, `id-token: write`
- job `request-reviewers`: `pull-requests: write`

## API / Interface

`workflow_call` contract:

- No inputs.
- No declared secrets at the wrapper level; the `run` job uses `secrets: inherit` for nested reusable workflow secrets.

Ingress does not pass `allowed-bot-users` for this generic path; the upstream lock workflow uses its built-in defaults (no control-plane issue author list).

## References

- Client template: [obs-aw-client-template.md](obs-aw-client-template.md) — registry id `issue-fixer`
- Routing rules: [docs/routing/issue-fixer-routing.md](../routing/issue-fixer-routing.md)
- Upstream lock: [elastic/ai-github-actions](https://github.com/elastic/ai-github-actions) — [`.github/workflows/gh-aw-issue-fixer.lock.yml`](https://github.com/elastic/ai-github-actions/blob/main/.github/workflows/gh-aw-issue-fixer.lock.yml)

# Workflow: `oblt-aw-mention-in-issue.yml`

## Overview

Source file: `.github/workflows/oblt-aw-mention-in-issue.yml`

Reusable wrapper that calls the locked mention-in-issue workflow in `elastic/ai-github-actions`. The event-scoped client/orchestrator path is `trigger-oblt-aw-issue-comment.yml` → `oblt-aw-event-issue-comment.yml` → this workflow when prelude allows `obs:mention-in-issue`.

## Prerequisites

- Triggered via `workflow_call` from `oblt-aw-event-issue-comment.yml` (invoked by the `trigger-oblt-aw-issue-comment.yml` client template).
- Required secret: `COPILOT_GITHUB_TOKEN`.

## Usage

Ingress routes here when:

- `github.event_name == 'issue_comment'` and `github.event.action == 'created'`, and
- `github.event.issue.pull_request == null` (the comment is on an issue, not a PR), and
- `startsWith(github.event.comment.body, '/ai')`, and
- comment does not start with `/ai implement` (reserved for the generic issue-fixer route), and
- `github.event.comment.author_association` is one of `OWNER`, `MEMBER`, or `COLLABORATOR`, and
- Dashboard gating allows `mention-in-issue` (or no dashboard issue is present, so all workflows are enabled).

This wrapper first runs `resolve-apm-assets` with the same route predicate used by `mention-in-issue` and then passes resolved `additional-instructions` to the upstream lock workflow. `resolve-apm-assets` requires `id-token: write`.

The job `mention-in-issue` calls:

- `elastic/ai-github-actions/.github/workflows/gh-aw-mention-in-issue.lock.yml@main`

Behavior and agent instructions for the locked workflow are defined in `elastic/ai-github-actions`.

## Troubleshooting

- A `/ai` comment from non-collaborators (for example, `CONTRIBUTOR`, `NONE`, or `FIRST_TIMER`) will not run this route because `oblt-aw-mention-in-issue.yml` requires author association `OWNER`/`MEMBER`/`COLLABORATOR`.

## Configuration

Permissions:

- Workflow-level: `contents: read`
- `resolve-apm-assets` job: `contents: read`, `id-token: write`
- `mention-in-issue` job: `actions: read`, `contents: write`, `discussions: write`, `issues: write`, `pull-requests: write`

## API / Interface

`workflow_call` contract:

- Input: `shared-proceed` (`required: true`, `type: string`)
- Input: `shared-allowed-pr-authors-json` (`required: true`, `type: string`)
- Input: `shared-allowed-pr-authors-csv` (`required: true`, `type: string`)
- Input: `shared-allowed-issue-authors-json` (`required: true`, `type: string`)
- Input: `shared-allowed-issue-authors-csv` (`required: true`, `type: string`)
- Input: `shared-token-policy` (`required: true`, `type: string`)
- Secret: `COPILOT_GITHUB_TOKEN` (`required: true`)

## References

- Client template: [oblt-aw-client-template.md](oblt-aw-client-template.md) — registry id `mention-in-issue`
- Upstream lock: `elastic/ai-github-actions` — `.github/workflows/gh-aw-mention-in-issue.lock.yml`
- Upstream docs: `elastic/ai-github-actions` — `docs/workflows/gh-agent-workflows/mention-in-issue.md`

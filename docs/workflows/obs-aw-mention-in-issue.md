# Workflow: `obs-aw-mention-in-issue.yml`

## Overview

Source file: `.github/workflows/obs-aw-mention-in-issue.yml`

Reusable wrapper that calls the locked mention-in-issue workflow in `elastic/ai-github-actions`. The client template `trigger-obs-aw-mention-in-issue.yml` calls this workflow on `issue_comment` events when prelude allows `obs:mention-in-issue`.

## Prerequisites

- Triggered via `workflow_call` from `trigger-obs-aw-mention-in-issue.yml` client templates.

## Usage

Ingress routes here when:

- `github.event_name == 'issue_comment'` and `github.event.action == 'created'`, and
- `github.event.issue.pull_request == null` (the comment is on an issue, not a PR), and
- `startsWith(github.event.comment.body, '/ai')`, and
- comment does not start with `/ai implement` (reserved for the generic issue-fixer route), and
- `github.event.comment.author_association` is one of `OWNER`, `MEMBER`, or `COLLABORATOR`, and
- Dashboard gate passes for registry id `mention-in-issue` (`enabled-workflows` contains `obs:mention-in-issue`).

Comment prefix and author-association checks are enforced in `obs-aw-mention-in-issue.yml` after prelude.

The job `mention-in-issue` calls:

- `elastic/ai-github-actions/.github/workflows/gh-aw-mention-in-issue.lock.yml@main`

Behavior and agent instructions for the locked workflow are defined in `elastic/ai-github-actions`.

## Troubleshooting

- A `/ai` comment from non-collaborators (for example, `CONTRIBUTOR`, `NONE`, or `FIRST_TIMER`) will not route to `obs-aw-mention-in-issue` because ingress blocks author associations outside `OWNER`/`MEMBER`/`COLLABORATOR`.

## Configuration

Permissions:

- `actions: read`
- `contents: write`
- `discussions: write`
- `issues: write`
- `pull-requests: write`

## API / Interface

`workflow_call` contract:


## References

- Client template: [obs-aw-client-template.md](obs-aw-client-template.md) — registry id `mention-in-issue`
- Upstream lock: `elastic/ai-github-actions` — `.github/workflows/gh-aw-mention-in-issue.lock.yml`
- Upstream docs: `elastic/ai-github-actions` — `docs/workflows/gh-agent-workflows/mention-in-issue.md`

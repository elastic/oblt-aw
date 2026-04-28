# Workflow: `gh-aw-mention-in-issue.yml`

## Overview

Source file: `.github/workflows/gh-aw-mention-in-issue.yml`

Reusable wrapper that calls the locked mention-in-issue workflow in `elastic/ai-github-actions`. The client entrypoint (`oblt-aw` template) invokes `oblt-aw-ingress`, which runs this job when a `/ai` comment is posted on an issue and the workflow is enabled on the control-plane dashboard.

## Prerequisites

- Triggered via `workflow_call` from `oblt-aw-ingress.yml`.
- Required secret: `COPILOT_GITHUB_TOKEN`.

## Usage

Ingress routes here when:

- `github.event_name == 'issue_comment'` and `github.event.action == 'created'`, and
- `github.event.issue.pull_request == null` (the comment is on an issue, not a PR), and
- `startsWith(github.event.comment.body, '/ai')`, and
- comment does not start with `/ai implement` (reserved for the generic issue-fixer route), and
- `github.event.comment.author_association` is one of `OWNER`, `MEMBER`, or `COLLABORATOR`, and
- Dashboard gating allows `mention-in-issue` (or no dashboard issue is present, so all workflows are enabled).

This allow-list check is enforced in ingress routing (`.github/workflows/oblt-aw-ingress.yml`) before `gh-aw-mention-in-issue.yml` is called.

The job `mention-in-issue` calls:

- `elastic/ai-github-actions/.github/workflows/gh-aw-mention-in-issue.lock.yml@main`

Behavior and agent instructions for the locked workflow are defined in `elastic/ai-github-actions`.

## Troubleshooting

- A `/ai` comment from non-collaborators (for example, `CONTRIBUTOR`, `NONE`, or `FIRST_TIMER`) will not route to `gh-aw-mention-in-issue` because ingress blocks author associations outside `OWNER`/`MEMBER`/`COLLABORATOR`.

## Configuration

Permissions:

- `actions: read`
- `contents: write`
- `discussions: write`
- `issues: write`
- `pull-requests: write`

## API / Interface

`workflow_call` contract:

- Secret: `COPILOT_GITHUB_TOKEN` (`required: true`)

## References

- Ingress routing: `docs/workflows/oblt-aw-ingress.md` — workflow id `mention-in-issue` in `workflow-registry.json`
- Upstream lock: `elastic/ai-github-actions` — `.github/workflows/gh-aw-mention-in-issue.lock.yml`
- Upstream docs: `elastic/ai-github-actions` — `docs/workflows/gh-agent-workflows/mention-in-issue.md`

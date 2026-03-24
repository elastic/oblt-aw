# Workflow: `gh-aw-issue-triage.yml`

## Overview

Source file: `.github/workflows/gh-aw-issue-triage.yml`

Reusable wrapper that calls the locked generic issue-triage workflow in `elastic/ai-github-actions`. The client entrypoint (`oblt-aw` template) invokes `oblt-aw-ingress`, which runs this job when an issue is opened and the workflow is enabled on the control-plane dashboard.

## Prerequisites

- Triggered via `workflow_call` from `oblt-aw-ingress.yml`.
- Required secret: `COPILOT_GITHUB_TOKEN`.

## Usage

Ingress routes here when:

- `github.event_name == 'issues'` and `github.event.action == 'opened'`, and
- Dashboard gating allows `issue-triage` (or no dashboard issue is present, so all workflows are enabled).

The job `run` calls:

- `elastic/ai-github-actions/.github/workflows/gh-aw-issue-triage.lock.yml@main`

Behavior and agent instructions for the locked workflow are defined in `elastic/ai-github-actions`.

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

## References

- Ingress routing: `docs/workflows/oblt-aw-ingress.md` — workflow id `issue-triage` in `workflow-registry.json`
- Specialized triage (Resource Not Accessible by Integration): `docs/workflows/gh-aw-resource-not-accessible-by-integration-triage.md`
- Upstream lock: `elastic/ai-github-actions` — `.github/workflows/gh-aw-issue-triage.lock.yml`

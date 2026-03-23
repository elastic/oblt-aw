# Workflow: `gh-aw-issue-triage.yml`

## Overview

Source file: `.github/workflows/gh-aw-issue-triage.yml`

This workflow runs when a new issue is opened and delegates execution to the locked issue-triage reusable workflow in `elastic/ai-github-actions`.

## Prerequisites

- Repository secret: `COPILOT_GITHUB_TOKEN` (passed to the reusable workflow).

## Usage

Triggers:

- `issues` with type `opened`

The job `run` calls:

- `elastic/ai-github-actions/.github/workflows/gh-aw-issue-triage.lock.yml@main`

Behavior, inputs, and agent instructions for the locked workflow are defined in the `elastic/ai-github-actions` repository; this repository only provides the event entrypoint and secret wiring.

## Configuration

Permissions declared in the workflow file:

- `actions: read`
- `contents: read`
- `discussions: write`
- `issues: write`
- `pull-requests: write`

## API / Interface

Event entrypoint (not `workflow_call`):

| Item | Value |
|------|--------|
| Triggers | `issues: opened` |
| Secrets | `COPILOT_GITHUB_TOKEN` → reusable workflow |
| Reusable workflow | `gh-aw-issue-triage.lock.yml@main` |

## References

- Same lock workflow, ingress context: `docs/workflows/gh-aw-resource-not-accessible-by-integration-triage.md` (Resource Not Accessible by Integration triage wrapper uses `gh-aw-issue-triage.lock.yml` via `workflow_call`).
- Upstream lock definition: `elastic/ai-github-actions` — `.github/workflows/gh-aw-issue-triage.lock.yml`

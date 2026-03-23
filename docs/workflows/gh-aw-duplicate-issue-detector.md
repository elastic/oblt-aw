# Workflow: `gh-aw-duplicate-issue-detector.yml`

## Overview

Source file: `.github/workflows/gh-aw-duplicate-issue-detector.yml`

This workflow runs when a new issue is opened, or when invoked manually, and delegates execution to the locked duplicate-issue-detector reusable workflow in `elastic/ai-github-actions`.

## Prerequisites

- Repository secret: `COPILOT_GITHUB_TOKEN` (passed to the reusable workflow).

## Usage

Triggers:

- `issues` with type `opened`
- `workflow_dispatch` (manual runs)

The job `run` calls:

- `elastic/ai-github-actions/.github/workflows/gh-aw-duplicate-issue-detector.lock.yml@main`

Behavior, inputs, and agent instructions for the locked workflow are defined in the `elastic/ai-github-actions` repository; this repository only provides the event entrypoint and secret wiring.

## Configuration

Permissions declared in the workflow file:

- `contents: read`
- `discussions: write`
- `issues: write`
- `pull-requests: read`

## API / Interface

Event entrypoint (not `workflow_call`):

| Item | Value |
|------|--------|
| Triggers | `issues: opened`, `workflow_dispatch` |
| Secrets | `COPILOT_GITHUB_TOKEN` → reusable workflow |
| Reusable workflow | `gh-aw-duplicate-issue-detector.lock.yml@main` |

## References

- Upstream lock definition: `elastic/ai-github-actions` — `.github/workflows/gh-aw-duplicate-issue-detector.lock.yml`

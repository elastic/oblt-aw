# Workflow: `gh-aw-resource-not-accessible-by-integration-detector.yml`

## Overview

Source file: `.github/workflows/gh-aw-resource-not-accessible-by-integration-detector.yml`

This reusable workflow detects `Resource not accessible by integration` occurrences in workflow logs and creates issue output through the locked bug-hunter workflow.

## Prerequisites

- Triggered via `workflow_call`.
- Required secret: `COPILOT_GITHUB_TOKEN`.

## Usage

The job `run` calls:

- `elastic/ai-github-actions/.github/workflows/gh-aw-bug-hunter.lock.yml@main`

Repository filter behavior is controlled by input `target-repositories`:

- `[]` allows all repositories.
- non-empty arrays allow only listed repositories.

Configured instructions define:

- log scan scope (last 24 hours, all branches)
- required error metadata collection
- issue title prefix: `[AI Detector][Resource not accessible by Integration]`

## Configuration

Permissions:

- `actions: read`
- `contents: read`
- `issues: write`
- `pull-requests: read`

## API / Interface

`workflow_call` contract:

- Input: `target-repositories` (string JSON array, default `[]`)
- Secret: `COPILOT_GITHUB_TOKEN` (`required: true`)

## References

- Routing rules: `docs/routing/resource-not-accessible-by-integration-routing.md`

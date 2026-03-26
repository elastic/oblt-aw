# Workflow: `gh-aw-resource-not-accessible-by-integration-fixer.yml`

## Overview

Source file: `.github/workflows/gh-aw-resource-not-accessible-by-integration-fixer.yml`

This reusable workflow executes issue-based fixes for issues labeled as ready to fix in the Resource Not Accessible by Integration flow.

## Prerequisites

- Triggered via `workflow_call`.
- Issue labels must include:
  - `oblt-aw/ai/fix-ready`
  - `oblt-aw/triage/res-not-accessible-by-integration`

## Usage

The job `run` calls:

- `elastic/ai-github-actions/.github/workflows/gh-aw-issue-fixer.lock.yml@main`

Configured instructions require:

- strict execution of triage-generated plan
- least-privilege permission fixes
- draft PR first, then ready-for-review after validation
- reviewer request to `elastic/observablt-ci`
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

- Routing rules: `docs/routing/resource-not-accessible-by-integration-routing.md`

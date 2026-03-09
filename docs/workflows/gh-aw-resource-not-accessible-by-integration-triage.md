# Workflow: `gh-aw-resource-not-accessible-by-integration-triage.yml`

## Overview

Source file: `.github/workflows/gh-aw-resource-not-accessible-by-integration-triage.yml`

This reusable workflow triages newly opened issues for the `Resource not accessible by integration` problem class and prepares fix-ready issues.

## Prerequisites

- Triggered via `workflow_call`.
- Required secret: `COPILOT_GITHUB_TOKEN`.

## Usage

The job `run` calls:

- `elastic/ai-github-actions/.github/workflows/gh-aw-issue-triage.lock.yml@main`

Configured instructions define:

- classification criteria for Resource Not Accessible by Integration issues
- labels: `oblt-aw/triage/resource-not-accessible-by-integration`, `oblt-aw/triage/other`, `oblt-aw/triage/needs-info`
- when to set `oblt-aw/ai/fix-ready`
- required resolution plan structure

Repository filter behavior uses `target-repositories` with the same semantics as detector/fixer.

## Configuration

Permissions:

- `actions: read`
- `contents: read`
- `discussions: write`
- `issues: write`
- `pull-requests: write`

## API / Interface

`workflow_call` contract:

- Input: `target-repositories` (string JSON array, default `[]`)
- Secret: `COPILOT_GITHUB_TOKEN` (`required: true`)

## References

- Routing rules: `docs/routing/resource-not-accessible-by-integration-routing.md`

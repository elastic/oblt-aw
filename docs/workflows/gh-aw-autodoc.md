# Workflow: `gh-aw-autodoc.yml`

## Overview

Source file: `.github/workflows/gh-aw-autodoc.yml`

This reusable workflow automates documentation maintenance in two stages: audit for documentation drift, then open a docs-only PR when findings exist.

## Prerequisites

- Triggered via `workflow_call`.
- Required secret: `COPILOT_GITHUB_TOKEN`.

## Usage

Jobs:

- `audit`: calls `gh-aw-docs-patrol.lock.yml` to analyze docs and create an issue with actionable findings.
- `fix`: calls `gh-aw-create-pr-from-issue.lock.yml` only when `audit` created an issue.

Workflow-specific requirements passed to the PR stage:

- PR title must be `docs: Documentation analysis and improvement`
- PR body must include analyzed files, issues found, and changes made
- only documentation files may be changed

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

- Routing notes: `.github/workflow-routing/autodoc/README.md`

# Workflow: `gh-aw-autodoc.yml`

## Overview

Source file: [.github/workflows/gh-aw-autodoc.yml](../../.github/workflows/gh-aw-autodoc.yml)

This reusable workflow automates documentation maintenance in two stages: audit for documentation drift, then open a docs-only PR when findings exist.

## Prerequisites

- Triggered via `workflow_call`.
- Required secret: `COPILOT_GITHUB_TOKEN`.

## Usage

Jobs:

- `audit`: calls `gh-aw-docs-patrol.lock.yml` to analyze docs and create an issue with actionable findings. Created issues always @mention `@elastic/observablt-ci` in the body so the team receives notifications.
- `fix`: calls `gh-aw-create-pr-from-issue.lock.yml` only when `audit` created an issue.
- `finalize-pr`: requests a review from `@elastic/observablt-ci` and applies the `changelog:docs` label to the created PR if that label exists in the repository.

Workflow-specific requirements passed to the PR stage:

- PR title must be `docs: Documentation analysis and improvement`
- PR body must include analyzed files, issues found, and changes made
- only documentation files may be changed

Additional guidance encoded in `additional-instructions` for both audit and fix jobs:

- Treat leading `-` (and similar) in **table cells** as potentially intentional (for example icon or status placeholders); avoid “cleaning” them without evidence of a real defect.
- Do not hand-edit **auto-generated** documentation in the fix PR (docs-only); the audit should steer fixes toward generators, templates, or other sources of truth, and the PR body should record any follow-up that is outside this workflow’s scope.
- Preserve or lightly refresh **legacy inline comments** that still document useful context or history; avoid deleting them only for brevity.

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

- Routing rules: [docs/routing/autodoc-routing.md](../routing/autodoc-routing.md)

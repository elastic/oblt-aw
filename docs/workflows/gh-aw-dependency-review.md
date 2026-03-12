# Workflow: `gh-aw-dependency-review.yml`

## Overview

Source file: `.github/workflows/gh-aw-dependency-review.yml`

This reusable workflow delegates dependency-update PR analysis to a locked workflow in `elastic/ai-github-actions`.

## Prerequisites

- Triggered via `workflow_call`.
- Required secret: `COPILOT_GITHUB_TOKEN`.

## Usage

The job `run` calls:

- `elastic/ai-github-actions/.github/workflows/gh-aw-dependency-review.lock.yml@main`

Configured inputs include:

- `allowed-bot-users`: `dependabot[bot],renovate[bot],Dependabot,Renovate,elastic-vault-github-plugin-prod[bot]`
- `classification-labels`: `oblt-aw/ai/merge-ready`
- `additional-instructions`: CVE-focused and internal-change impact analysis instructions.

Labeling semantics (in additional-instructions):

- add `oblt-aw/ai/merge-ready` when: no CVE/GHSA/security fixes, no breaking changes affecting this repo, ecosystem checks pass, and workflows are testable or dependency is dev-only. "Low risk" is sufficient when criteria are met; minor behavioral changes that don't affect repo usage do not disqualify.

## Configuration

Permissions:

- `actions: read`
- `contents: read`
- `issues: write`
- `pull-requests: write`

## API / Interface

`workflow_call` contract:

- Secret: `COPILOT_GITHUB_TOKEN` (`required: true`)

## References

- Routing rules: `docs/routing/dependency-review-routing.md`

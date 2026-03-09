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
- `additional-instructions`: CVE-focused and internal-change impact analysis instructions.

Labeling extension configured in instructions:

- add `oblt-aw/ai/merge-ready` only when analysis is fully successful.

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

# Workflow: `gh-aw-security-fixer.yml`

## Overview

Source file: `.github/workflows/gh-aw-security-fixer.yml`

This reusable workflow executes issue-based fixes for security vulnerabilities. It calls `gh-aw-issue-fixer` from `elastic/ai-github-actions` with security-specific instructions. The upstream workflow is fetched from `elastic/ai-github-actions@main` at runtime.

## Prerequisites

- Triggered via `workflow_call`.
- Issue labels must include:
  - `oblt-aw/ai/fix-ready`
  - At least one of: `oblt-aw/triage/security-injection`, `oblt-aw/triage/security-secrets`, `oblt-aw/triage/security-supply-chain`, `oblt-aw/triage/security-least-privilege`

## Usage

The job `run` calls:

- `elastic/ai-github-actions/.github/workflows/gh-aw-issue-fixer.lock.yml@main`

Configured instructions require:

- strict execution of triage-generated resolution plan
- **least-privilege**: grant only minimum permissions required; no over-broad scopes
- **env-indirection**: never interpolate secrets/tokens in command strings; always pass via `env:` blocks
- draft PR first, then ready-for-review after validation
- reviewer request to `elastic/observablt-ci`
- no auto-merge

Repository filter behavior uses `target-repositories` with default `[]` as allow-all.

## Configuration

Permissions:

- `actions: read`
- `contents: write`
- `discussions: write`
- `issues: write`
- `pull-requests: write`

## API / Interface

`workflow_call` contract:

- Input: `target-repositories` (string JSON array, default `[]`)
- Secret: `COPILOT_GITHUB_TOKEN` (required)

## References

- Routing rules: `docs/routing/security-routing.md`
- Plan: `docs/plans/issue-3758-security-agentic-workflows-plan.md`

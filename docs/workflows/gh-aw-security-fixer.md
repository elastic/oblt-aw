# Workflow: `gh-aw-security-fixer.yml`

## Overview

Source file: [.github/workflows/gh-aw-security-fixer.yml](../../.github/workflows/gh-aw-security-fixer.yml)

This reusable workflow executes issue-based fixes for security vulnerabilities. It calls [elastic/ai-github-actions/.github/workflows/gh-aw-issue-fixer.lock.yml@main](https://github.com/elastic/ai-github-actions/blob/main/.github/workflows/gh-aw-issue-fixer.lock.yml) via `workflow_call` with security-specific instructions (no separate clone of [elastic/ai-github-actions](https://github.com/elastic/ai-github-actions)). Remediation scope follows the ruleset in [docs/workflows/security-scanning-ruleset.md](security-scanning-ruleset.md) and triage resolution plans.

## Prerequisites

- Triggered via `workflow_call`.
- Issue labels must include:
  - `oblt-aw/ai/fix-ready`
  - At least one of: `oblt-aw/triage/security-injection`, `oblt-aw/triage/security-secrets`, `oblt-aw/triage/security-supply-chain`, `oblt-aw/triage/security-least-privilege`

## Usage

The job `run` calls:

- [elastic/ai-github-actions/.github/workflows/gh-aw-issue-fixer.lock.yml@main](https://github.com/elastic/ai-github-actions/blob/main/.github/workflows/gh-aw-issue-fixer.lock.yml)

Configured instructions require:

- strict execution of triage-generated resolution plan
- **least-privilege**: grant only minimum permissions required; no over-broad scopes
- **env-indirection**: never interpolate secrets/tokens in command strings; always pass via `env:` blocks
- draft PR first, then ready-for-review after validation
- reviewer request to [elastic/observablt-ci](https://github.com/elastic/observablt-ci)
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

- Routing rules: [docs/routing/security-routing.md](../routing/security-routing.md)
- Security scanning ruleset: [docs/workflows/security-scanning-ruleset.md](security-scanning-ruleset.md)

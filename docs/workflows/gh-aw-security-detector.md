# Workflow: `gh-aw-security-detector.yml`

## Overview

Source file: `.github/workflows/gh-aw-security-detector.yml`

This reusable workflow scans repository code (shell scripts and workflow YAML) for security vulnerabilities and creates issues with structured findings. It implements the detector stage of the security agent pipeline described in `docs/architecture/security-agent-architecture.md`.

Unlike the resource-not-accessible detector (which searches workflow logs via an agent), the security detector runs static analysis tools directly: shellcheck for shell scripts and grep-based pattern checks for token exposure in workflow files.

## Prerequisites

- Triggered via `workflow_call`.
- Required secret: `COPILOT_GITHUB_TOKEN`.

## Usage

The workflow uses two jobs:

1. **fetch-ai-github-actions** — Fetches `elastic/ai-github-actions` to verify availability and discover workflow options used by triage and fixer stages.
2. **scan** — Checks out the repository, runs the security scan script, and creates issues from findings:
   - Discovers shell scripts (`*.sh`, `*.bash`) and workflow YAML (`.github/workflows/*.yml`)
   - Runs shellcheck on shell scripts
   - Runs pattern checks for `${{ secrets.* }}` in workflow files (SEC-002)
   - Creates one issue per finding with title prefix `[oblt-aw][security]`

The detector runs in the repository that invokes it (via ingress schedule or workflow_dispatch).

## Scan Logic

The scan script (`.github/scripts/security-scan.sh`) implements:

- **Shell scripts**: shellcheck with JSON output; findings reported as SHELLCHECK rule
- **Workflow YAML**: grep for `${{ secrets.` pattern (SEC-002 — token exposure in command context)

See `docs/workflows/security-scanning-ruleset.md` for full rule definitions and remediation guidance.

## Configuration

Permissions:

- `actions: read`
- `contents: read`
- `issues: write`
- `pull-requests: read`

## API / Interface

`workflow_call` contract:

- Secret: `COPILOT_GITHUB_TOKEN` (`required: true`)

## References

- [Security agent architecture](architecture/security-agent-architecture.md)
- [Security scanning ruleset](security-scanning-ruleset.md)
- [Implementation plan: issue #3758](../plans/issue-3758-security-agentic-workflows-plan.md)
- [elastic/oblt-actions#500](https://github.com/elastic/oblt-actions/issues/500) — token exposure via CLI args

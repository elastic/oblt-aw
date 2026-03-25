# Workflow: `gh-aw-security-triage.yml`

## Overview

Source file: `.github/workflows/gh-aw-security-triage.yml`

This reusable workflow triages newly opened security-related issues and prepares fix-ready issues for the security fixer workflow. It classifies vulnerabilities in GitHub Actions workflows and shell scripts: injection, secret management, supply chain, and least privilege—matching `docs/workflows/security-scanning-ruleset.md` and [elastic/observability-robots#3758](https://github.com/elastic/observability-robots/issues/3758). It runs in the **caller repository** (same as the detector).

## Prerequisites

- Triggered via `workflow_call`.
- Required secret: `COPILOT_GITHUB_TOKEN`.

## Usage

The job `run` calls:

- `elastic/ai-github-actions/.github/workflows/gh-aw-issue-triage.lock.yml@main`

Configured instructions define:

- classification criteria for security vulnerability issues
- labels: `oblt-aw/triage/security-injection`, `oblt-aw/triage/security-secrets`, `oblt-aw/triage/security-supply-chain`, `oblt-aw/triage/security-least-privilege`, `oblt-aw/triage/other`, `oblt-aw/triage/needs-info`
- when to set `oblt-aw/ai/fix-ready`
- required resolution plan structure: root cause, risk assessment, remediation steps, before/after examples

## Configuration

Permissions:

- `actions: read`
- `contents: read`
- `discussions: write`
- `issues: write`
- `pull-requests: write`

## API / Interface

`workflow_call` contract:

- Secret: `COPILOT_GITHUB_TOKEN` (`required: true`)

## Resolution Plan Structure

The triage agent appends a resolution plan to confirmed security issues with:

1. **Root Cause** — Vulnerable code location and pattern
2. **Risk Assessment** — Severity, impact, affected scope
3. **Remediation Steps** — Prioritized concrete changes
4. **Before / After Examples** — Vulnerable vs secure code snippets

## References

- [GitHub Actions Security Hardening](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)
- Routing rules: `docs/routing/security-routing.md`

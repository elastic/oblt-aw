# Workflow: `gh-aw-resource-not-accessible-by-integration-fixer.yml`

## Overview

Source file: [.github/workflows/gh-aw-resource-not-accessible-by-integration-fixer.yml](../../.github/workflows/gh-aw-resource-not-accessible-by-integration-fixer.yml)

This reusable workflow executes issue-based fixes for issues labeled as ready to fix in the Resource Not Accessible by Integration flow.

## Prerequisites

- Triggered via `workflow_call`.
- Issue labels must include:
  - `oblt-aw/ai/fix-ready`
  - `oblt-aw/triage/res-not-accessible-by-integration`

## Usage

The job `res-not-accessible-integration-fixer` calls:

- [elastic/ai-github-actions/.github/workflows/gh-aw-issue-fixer.lock.yml@main](https://github.com/elastic/ai-github-actions/blob/main/.github/workflows/gh-aw-issue-fixer.lock.yml)

Configured instructions require:

- strict execution of triage-generated plan
- least-privilege permission fixes
- draft PR first, then ready-for-review after validation
- reviewer request to [elastic/observablt-ci](https://github.com/orgs/elastic/teams/observablt-ci)
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

- Input: `allowed-bot-users` (`required: true`) — comma-separated GitHub logins for the upstream issue fixer lock; ingress passes `allowed_issue_authors_csv` from [allowed_issue_authors.json](https://github.com/elastic/oblt-aw/blob/main/config/obs/allowed_issue_authors.json).

## References

- Routing rules: [docs/routing/resource-not-accessible-by-integration-routing.md](../routing/resource-not-accessible-by-integration-routing.md)

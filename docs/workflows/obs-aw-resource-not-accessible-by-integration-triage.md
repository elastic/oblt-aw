# Workflow: `obs-aw-resource-not-accessible-by-integration-triage.yml`

## Overview

Source file: [.github/workflows/obs-aw-resource-not-accessible-by-integration-triage.yml](../../.github/workflows/obs-aw-resource-not-accessible-by-integration-triage.yml)

This reusable workflow triages issues that carry the detector label `oblt-aw/detector/res-not-accessible-by-integration` for the `Resource not accessible by integration` problem class and prepares fix-ready issues.

## Prerequisites

- Triggered via `workflow_call`.

## Usage

The job `res-not-accessible-integration-triage` calls:

- [elastic/ai-github-actions/.github/workflows/gh-aw-issue-triage.lock.yml@main](https://github.com/elastic/ai-github-actions/blob/main/.github/workflows/gh-aw-issue-triage.lock.yml)

The nested workflow receives **`classification-labels`** for `oblt-aw/triage/res-not-accessible-by-integration`, `oblt-aw/triage/other`, `oblt-aw/triage/needs-info`, and `oblt-aw/ai/fix-ready`.

Configured instructions define:

- classification criteria for Resource Not Accessible by Integration issues
- labels: `oblt-aw/triage/res-not-accessible-by-integration`, `oblt-aw/triage/other`, `oblt-aw/triage/needs-info`
- when to set `oblt-aw/ai/fix-ready`
- required resolution plan structure

The nested lock workflow mints an OIDC ephemeral token (`mint-ephemeral-token: true`) in the same job that applies labels, so `oblt-aw/ai/fix-ready` re-triggers the fixer route.

## Configuration

Permissions:

- **Workflow default:** `contents: read`
- **Job `res-not-accessible-integration-triage`:** `actions: read`, `contents: read`, `discussions: write`, `issues: write`, `pull-requests: write`, `id-token: write`

## API / Interface

`workflow_call` contract:

- Input: `allowed-bot-users` (`required: true`) — comma-separated GitHub logins for the upstream issue triage lock; ingress passes `allowed_issue_authors_csv` from [allowed_issue_authors.json](https://github.com/elastic/oblt-aw/blob/main/config/obs/allowed_issue_authors.json).

## References

- Routing rules: [docs/routing/resource-not-accessible-by-integration-routing.md](../routing/resource-not-accessible-by-integration-routing.md)

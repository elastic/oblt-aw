# Workflow: `gh-aw-resource-not-accessible-by-integration-triage.yml`

## Overview

Source file: [.github/workflows/gh-aw-resource-not-accessible-by-integration-triage.yml](../../.github/workflows/gh-aw-resource-not-accessible-by-integration-triage.yml)

This reusable workflow triages issues that carry the detector label `oblt-aw/detector/res-not-accessible-by-integration` for the `Resource not accessible by integration` problem class and prepares fix-ready issues.

## Prerequisites

- Triggered via `workflow_call`.
- Required secret: `COPILOT_GITHUB_TOKEN`.
- **Job `mint-gh-aw-github-token`:** `contents: read`, `id-token: write` (OIDC for ephemeral `create-token` with no explicit `token-policy`; catalog-info auto role for this workflow file).

## Usage

The job `mint-gh-aw-github-token` mints an installation token via [`elastic/oblt-actions/github/create-token@v1`](https://github.com/elastic/oblt-actions/tree/v1/github/create-token). The job `res-not-accessible-integration-triage` calls:

- [elastic/ai-github-actions/.github/workflows/gh-aw-issue-triage.lock.yml@copilot/add-classification-labels-input](https://github.com/elastic/ai-github-actions/blob/copilot/add-classification-labels-input/.github/workflows/gh-aw-issue-triage.lock.yml) (switch to `@main` after upstream merge)

The nested workflow receives **`GH_AW_GITHUB_TOKEN`** (mint output) and **`classification-labels`** for `oblt-aw/triage/res-not-accessible-by-integration`, `oblt-aw/triage/other`, `oblt-aw/triage/needs-info`, and `oblt-aw/ai/fix-ready`.

Configured instructions define:

- classification criteria for Resource Not Accessible by Integration issues
- labels: `oblt-aw/triage/res-not-accessible-by-integration`, `oblt-aw/triage/other`, `oblt-aw/triage/needs-info`
- when to set `oblt-aw/ai/fix-ready`
- required resolution plan structure

## Configuration

Permissions:

- **Workflow default:** `actions: read`, `contents: read`
- **Job `mint-gh-aw-github-token`:** `contents: read`, `id-token: write`
- **Job `res-not-accessible-integration-triage`:** `actions: read`, `contents: read`, `discussions: write`, `issues: write`, `pull-requests: write`

## API / Interface

`workflow_call` contract:

- Secret: `COPILOT_GITHUB_TOKEN` (`required: true`)

## References

- Routing rules: [docs/routing/resource-not-accessible-by-integration-routing.md](../routing/resource-not-accessible-by-integration-routing.md)

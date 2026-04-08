# Workflow: `gh-aw-automerge.yml`

## Overview

Source file: [.github/workflows/gh-aw-automerge.yml](../../.github/workflows/gh-aw-automerge.yml)

This workflow runs for a **single** pull request identified by the required `workflow_call` input `pull-request-number` (ingress passes the number from `pull_request` or `check_run`). It validates the PR with `GITHUB_TOKEN`, runs the GH-AW mention-in-pr approval step when validation passes, then enables squash auto-merge when checks and an `github-actions[bot]` approval are present.

Ingress selects which events dispatch here; see [Automerge routing](../routing/automerge-routing.md).

## Prerequisites

- Triggered via `workflow_call` when ingress matches the automerge routing rules (see ingress).
- For `pull_request` events, ingress pre-filters author and merge-ready label; for `check_run` (`completed`), ingress only requires an associated PR and excludes oblt-aw automerge-related check names so `scripts/validateAutomergePr.ts` still enforces author, label, draft/fork/ref, and check-runs.

## Usage

Jobs:

- `verify`: checks out control-plane scripts, runs `scripts/validateAutomergePr.ts` for `inputs.pull-request-number` (author allow list aligned with dependency-review, merge-ready label, draft/fork/ref, check-runs via Checks API — excluding the current workflow run’s own checks).
- `approve`: invokes `elastic/ai-github-actions` `gh-aw-mention-in-pr.lock.yml` when `verify` sets `proceed` (Copilot must not call check APIs; workflow already verified check-runs).
- `enable-automerge`: runs `scripts/enableAutomergeForApprovedPr.ts` for the same PR number to enable GraphQL auto-merge (squash) when other checks pass and `github-actions[bot]` has approved (same exclusion of this run’s checks).

There is no discover step. Merge-ready label and allowed actor are enforced in `validateAutomergePr.ts` and in ingress for `pull_request` paths (constants kept in sync with dependency-review).

## Configuration

Permissions:

- `actions: read`
- `checks: read`
- `contents: write`
- `discussions: write`
- `issues: write`
- `pull-requests: write`

## API / Interface

`workflow_call` contract:

- **Inputs:** `pull-request-number` (number, required) — PR to validate; ingress sets this from `github.event.pull_request.number` or `github.event.check_run.pull_requests[0].number`.
- **Secrets:** `COPILOT_GITHUB_TOKEN` (required) — forwarded from the ingress caller for the GH-AW approval job.

## References

- Routing rules: [docs/routing/automerge-routing.md](../routing/automerge-routing.md)

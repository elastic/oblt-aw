# Workflow: `gh-aw-automerge.yml`

## Overview

Source file: [.github/workflows/gh-aw-automerge.yml](../../.github/workflows/gh-aw-automerge.yml)

This workflow runs for a **single** pull request carried by the caller’s `github.event` (`pull_request` only). It validates the PR with `GITHUB_TOKEN`, runs the GH-AW mention-in-pr approval step when validation passes, then enables squash auto-merge when checks and an `github-actions[bot]` approval are present.

Ingress selects which events dispatch here; see [Automerge routing](../routing/automerge-routing.md).

## Prerequisites

- Triggered via `workflow_call` only when ingress has already matched author, `oblt-aw/ai/merge-ready` on the PR, and the right event (see ingress).
- `github.event.pull_request` must be populated (same as dependency-review PR flows).

## Usage

Jobs:

- `verify`: checks out control-plane scripts, runs `scripts/validateAutomergePr.ts` for `github.event.pull_request.number` (author allow list aligned with dependency-review, merge-ready label, draft/fork/ref, check-runs via Checks API).
- `approve`: invokes `elastic/ai-github-actions` `gh-aw-mention-in-pr.lock.yml` when `verify` sets `proceed` (Copilot must not call check APIs; workflow already verified check-runs).
- `enable-automerge`: runs `scripts/enableAutomergeForApprovedPr.ts` for the same PR number to enable GraphQL auto-merge (squash) when checks pass and `github-actions[bot]` has approved.

There is no discover step and no `workflow_call` inputs for merge-ready label or allowed actor (constants live in `validateAutomergePr.ts` and ingress, kept in sync with dependency-review).

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

- **Secrets:** `COPILOT_GITHUB_TOKEN` (required) — forwarded from the ingress caller for the GH-AW approval job.

## References

- Routing rules: [docs/routing/automerge-routing.md](../routing/automerge-routing.md)

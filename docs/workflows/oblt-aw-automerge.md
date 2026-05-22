# Workflow: `oblt-aw-automerge.yml`

## Overview

Source file: [.github/workflows/oblt-aw-automerge.yml](../../.github/workflows/oblt-aw-automerge.yml)

This workflow runs for a **single** pull request from `github.event.pull_request` (`pull_request` trigger only). It validates the PR with `GITHUB_TOKEN`, runs the GH-AW mention-in-pr approval step when validation passes, then runs **pascalgn/automerge-action** in the `automerge` job so the PR can squash-merge when labels, reviews, and checks satisfy configuration. If that merge attempt reports `merge_failed` (for example when merge queue is required), the workflow runs `enable-merge-when-ready` to enable native GitHub auto-merge (`gh pr merge --auto --squash`) as a fallback. Required status checks are **not** queried in `verify`; branch protection and merge readiness checks handle gating before merge.

Ingress selects which events dispatch here; see [Automerge routing](../routing/automerge-routing.md).

## Prerequisites

- Triggered via `workflow_call` from `trg-oblt-aw-automerge.yml` when prelude and route guards match author, `oblt-aw/ai/merge-ready`, and the right `pull_request` action.
- `github.event.pull_request` must be populated (same as dependency-review PR flows).

## Usage

Jobs:

- `verify`: shallow sparse checkout of `elastic/oblt-aw` (`allowed_pr_authors.json`, `validateAutomergePr.ts`, and npm manifests only), then runs `scripts/obs/validateAutomergePr.ts` for `github.event.pull_request.number` (author allow list aligned with dependency-review, merge-ready label, draft/fork/ref).
- `check-dependency-collection`: shallow sparse checkout of `elastic/oblt-aw` (collection config, gate scripts, and `package.json` / lockfile only), then classifies the PR by changed file paths against [config/obs/automerge-dependency-collections.json](../../config/obs/automerge-dependency-collections.json); skips `approve`/`automerge` when the collection is not active and posts a PR comment explaining why (no extra labels in target repos).
- `approve`: invokes `elastic/ai-github-actions` `gh-aw-mention-in-pr.lock.yml` when `verify` and `check-dependency-collection` pass (Copilot must not call check-run APIs for gating; branch protection handles required checks at merge time).
- `automerge`: runs **pascalgn/automerge-action** with `GITHUB_TOKEN` on the **same** repository as the PR (`PULL_REQUEST` is the PR number). Squash-merge when `MERGE_LABELS`, `MERGE_REQUIRED_APPROVALS`, and GitHub mergeability align with branch protection.
- `enable-merge-when-ready`: runs only when `automerge` outputs `merge_failed`; creates an ephemeral token via `elastic/oblt-actions/github/create-token@v1` and enables native auto-merge queue behavior with `gh pr merge --auto --squash`.

There is no discover step. Prelude supplies **`allowed-pr-authors-csv`** into the `approve` job’s `oblt-aw-mention-in-pr` call. Merge-ready label and PR author gating remain in `validateAutomergePr.ts` and workflow `if` conditions; the canonical PR author list is [allowed_pr_authors.json](https://github.com/elastic/oblt-aw/blob/main/config/obs/allowed_pr_authors.json).

## Configuration

`GITHUB_TOKEN` follows least privilege: workflow root is `contents: read` only; each job sets the minimum scopes it needs.

| Job | Permissions |
|-----|-------------|
| Workflow (default) | `contents: read` |
| `verify` | `actions: read`, `contents: read`, `pull-requests: read` (validate script reads the PR) |
| `check-dependency-collection` | `contents: read`, `pull-requests: write` (list PR files, post or remove gate comment) |
| `approve` | `actions: read`, `contents: write`, `discussions: write`, `issues: write`, `pull-requests: write` (GH-AW mention-in-pr) |
| `automerge` | `contents: write`, `pull-requests: write` (automerge action merges the PR) |
| `enable-merge-when-ready` | `id-token: write` (required for ephemeral token minting before `gh pr merge --auto`) |

## API / Interface

`workflow_call` contract:

- **Allow list:** `needs.prelude.outputs.allowed-pr-authors-csv` for `gh-aw-mention-in-pr.lock.yml` (from [load-allowed-authors.yml](../../.github/workflows/load-allowed-authors.yml) via prelude).
- **Secrets:** `COPILOT_GITHUB_TOKEN` (required) — forwarded from the client caller for the GH-AW approval job.

## References

- Routing rules: [docs/routing/automerge-routing.md](../routing/automerge-routing.md)

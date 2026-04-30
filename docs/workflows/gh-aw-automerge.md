# Workflow: `gh-aw-automerge.yml`

## Overview

Source file: [.github/workflows/gh-aw-automerge.yml](../../.github/workflows/gh-aw-automerge.yml)

This workflow runs for a **single** pull request from `github.event.pull_request` (`pull_request` trigger only). It validates the PR with `GITHUB_TOKEN`, runs the GH-AW mention-in-pr approval step when validation passes, then runs **pascalgn/automerge-action** in the `automerge` job so the PR can squash-merge when labels, reviews, and checks satisfy configuration. If that merge attempt reports `merge_failed` (for example when merge queue is required), the workflow runs `enable-merge-when-ready` to enable native GitHub auto-merge (`gh pr merge --auto --squash`) as a fallback. Required status checks are **not** queried in `verify`; branch protection and merge readiness checks handle gating before merge.

Ingress selects which events dispatch here; see [Automerge routing](../routing/automerge-routing.md).

## Prerequisites

- Triggered via `workflow_call` when ingress matches author, `oblt-aw/ai/merge-ready` on the PR, and the right `pull_request` action (see ingress).
- `github.event.pull_request` must be populated (same as dependency-review PR flows).

## Usage

Jobs:

- `verify`: checks out control-plane scripts, runs `scripts/validateAutomergePr.ts` for `github.event.pull_request.number` (author allow list aligned with dependency-review, merge-ready label, draft/fork/ref).
- `approve`: invokes `elastic/ai-github-actions` `gh-aw-mention-in-pr.lock.yml` when `verify` sets `proceed` (Copilot must not call check-run APIs for gating; branch protection handles required checks at merge time).
- `automerge`: runs **pascalgn/automerge-action** with `GITHUB_TOKEN` on the **same** repository as the PR (`PULL_REQUEST` is the PR number). Squash-merge when `MERGE_LABELS`, `MERGE_REQUIRED_APPROVALS`, and GitHub mergeability align with branch protection.
- `enable-merge-when-ready`: runs only when `automerge` outputs `merge_failed`; creates an ephemeral token via `elastic/oblt-actions/github/create-token@v1` and enables native auto-merge queue behavior with `gh pr merge --auto --squash`.

There is no discover step. Ingress passes **`allowed-bot-users`** (CSV from `load-allowed-authors` → `allowed_pr_authors_csv`, same source as dependency-review) into the `approve` job’s `gh-aw-mention-in-pr` call so vault and other allowed bot actors match GH-AW’s bot gate. Merge-ready label and PR author gating remain in `validateAutomergePr.ts` and ingress `if` conditions; the canonical PR author list is [allowed_pr_authors.json](https://github.com/elastic/oblt-aw/blob/main/config/obs/allowed_pr_authors.json) on `elastic/oblt-aw`.

## Configuration

`GITHUB_TOKEN` follows least privilege: workflow root is `contents: read` only; each job sets the minimum scopes it needs.

| Job | Permissions |
|-----|-------------|
| Workflow (default) | `contents: read` |
| `verify` | `actions: read`, `contents: read`, `pull-requests: read` (validate script reads the PR) |
| `approve` | `actions: read`, `contents: write`, `discussions: write`, `issues: write`, `pull-requests: write` (GH-AW mention-in-pr) |
| `automerge` | `contents: write`, `pull-requests: write` (automerge action merges the PR) |
| `enable-merge-when-ready` | `id-token: write` (required for ephemeral token minting before `gh pr merge --auto`) |

## API / Interface

`workflow_call` contract:

- **Inputs:** `allowed-bot-users` (required) — comma-separated logins for `gh-aw-mention-in-pr.lock.yml`; ingress passes `needs.load-allowed-authors.outputs.allowed_pr_authors_csv` (see [load-allowed-authors.yml](../../.github/workflows/load-allowed-authors.yml)).
- **Secrets:** `COPILOT_GITHUB_TOKEN` (required) — forwarded from the ingress caller for the GH-AW approval job.

## References

- Routing rules: [docs/routing/automerge-routing.md](../routing/automerge-routing.md)

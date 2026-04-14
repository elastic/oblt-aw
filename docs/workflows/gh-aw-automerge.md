# Workflow: `gh-aw-automerge.yml`

## Overview

Source file: [.github/workflows/gh-aw-automerge.yml](../../.github/workflows/gh-aw-automerge.yml)

This workflow runs for a **single** pull request from `github.event.pull_request` (`pull_request` trigger only). It validates the PR with `GITHUB_TOKEN`, runs the GH-AW mention-in-pr approval step when validation passes, then enables squash auto-merge when `github-actions[bot]` has approved. Required status checks are **not** queried here; GitHub enforces them when merging via auto-merge.

Ingress selects which events dispatch here; see [Automerge routing](../routing/automerge-routing.md).

## Prerequisites

- Triggered via `workflow_call` when ingress matches author, `oblt-aw/ai/merge-ready` on the PR, and the right `pull_request` action (see ingress).
- `github.event.pull_request` must be populated (same as dependency-review PR flows).

## Usage

Jobs:

- `verify`: checks out control-plane scripts, runs `scripts/validateAutomergePr.ts` for `github.event.pull_request.number` (author allow list aligned with dependency-review, merge-ready label, draft/fork/ref).
- `approve`: invokes `elastic/ai-github-actions` `gh-aw-mention-in-pr.lock.yml` when `verify` sets `proceed` (Copilot must not call check-run APIs for gating; branch protection handles required checks at merge time).
- `request-enable-automerge`: sends a `repository_dispatch` event (`oblt-aw-automerge`) with the PR number so the actual enable step runs in [`automerge.yml`](../../.github/workflows/automerge.yml). That keeps the long GraphQL enable work off the PR’s check suite and reduces “unstable status” races while checks settle.

The enable workflow ([`automerge.yml`](../../.github/workflows/automerge.yml)) runs `scripts/enableAutomergeForApprovedPr.ts` to enable squash auto-merge when `github-actions[bot]` has approved.

There is no discover step and no `workflow_call` inputs for merge-ready label or allowed actor (constants live in `validateAutomergePr.ts` and ingress, kept in sync with dependency-review).

## Configuration

`GITHUB_TOKEN` follows least privilege: workflow root is `contents: read` only; each job sets the minimum scopes it needs.

| Job | Permissions |
|-----|-------------|
| Workflow (default) | `contents: read` |
| `verify` | `actions: write` (npm cache via `setup-node`; write includes read for this scope), `contents: read`, `pull-requests: read` (validate script reads the PR) |
| `approve` | `contents: read`, `issues: write`, `pull-requests: write` (GH-AW mention-in-pr) |
| `request-enable-automerge` | `contents: write` (create `repository_dispatch`; [GitHub requires write access to the repository](https://docs.github.com/en/rest/repos/repos#create-a-repository-dispatch-event)) |

[`automerge.yml`](../../.github/workflows/automerge.yml) (dispatch target): workflow root `contents: read`; job `enable` uses `actions: write` (npm cache), `contents: read`, and `pull-requests: write` for checkout of control-plane scripts and `enablePullRequestAutoMerge`.

## API / Interface

`workflow_call` contract:

- **Secrets:** `COPILOT_GITHUB_TOKEN` (required) — forwarded from the ingress caller for the GH-AW approval job.

## References

- Routing rules: [docs/routing/automerge-routing.md](../routing/automerge-routing.md)

# Workflow: `gh-aw-automerge.yml`

## Overview

Source file: [.github/workflows/gh-aw-automerge.yml](../../.github/workflows/gh-aw-automerge.yml)

This workflow runs for a **single** pull request from `github.event.pull_request` (`pull_request` trigger only). It validates the PR with `GITHUB_TOKEN`, runs the GH-AW mention-in-pr approval step when validation passes, then dispatches [`automerge.yml`](../../.github/workflows/automerge.yml) so a separate run can merge the PR when ready (see below). Required status checks are **not** queried in `verify`; branch protection and [`pascalgn/automerge-action`](https://github.com/pascalgn/automerge-action) handle readiness before merge.

Ingress selects which events dispatch here; see [Automerge routing](../routing/automerge-routing.md).

## Prerequisites

- Triggered via `workflow_call` when ingress matches author, `oblt-aw/ai/merge-ready` on the PR, and the right `pull_request` action (see ingress).
- `github.event.pull_request` must be populated (same as dependency-review PR flows).

## Usage

Jobs:

- `verify`: checks out control-plane scripts, runs `scripts/validateAutomergePr.ts` for `github.event.pull_request.number` (author allow list aligned with dependency-review, merge-ready label, draft/fork/ref).
- `approve`: invokes `elastic/ai-github-actions` `gh-aw-mention-in-pr.lock.yml` when `verify` sets `proceed` (Copilot must not call check-run APIs for gating; branch protection handles required checks at merge time).
- `request-enable-automerge`: runs [`automerge.yml`](../../.github/workflows/automerge.yml) via `gh workflow run` (`workflow_dispatch` input `pull-request-number`) so merge logic runs in a separate workflow run and is not attached as a long-lived check on the PR head commit.

The dispatch target [`automerge.yml`](../../.github/workflows/automerge.yml) calls [`load-allowed-pr-authors.yml`](../../.github/workflows/load-allowed-pr-authors.yml), validates the PR author against that output, then runs **pascalgn/automerge-action** to **squash-merge** the PR when labels, reviews, and checks satisfy its configuration (`MERGE_LABELS`, `MERGE_REQUIRED_APPROVALS`, etc.).

There is no discover step and no `workflow_call` inputs for merge-ready label or allowed actor on `gh-aw-automerge` (see `validateAutomergePr.ts` and ingress; allow list is centralized in `load-allowed-pr-authors` / `config/allowed_pr_authors.json`).

## Configuration

`GITHUB_TOKEN` follows least privilege: workflow root is `contents: read` only; each job sets the minimum scopes it needs.

| Job | Permissions |
|-----|-------------|
| Workflow (default) | `contents: read` |
| `verify` | `actions: write` (npm cache via `setup-node`; write includes read for this scope), `contents: read`, `pull-requests: read` (validate script reads the PR) |
| `approve` | `contents: read`, `issues: write`, `pull-requests: write` (GH-AW mention-in-pr) |
| `request-enable-automerge` | `actions: write` ([create a workflow dispatch event](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event)), `contents: read` |

[`automerge.yml`](../../.github/workflows/automerge.yml) (dispatch target): workflow root `contents: read`; job `allowed-pr-authors` uses `load-allowed-pr-authors.yml`; job `enable` needs it and uses `contents: write` and `pull-requests: write` for `gh` and the automerge action (no checkout of the control plane in `enable`).

## API / Interface

`workflow_call` contract:

- **Secrets:** `COPILOT_GITHUB_TOKEN` (required) — forwarded from the ingress caller for the GH-AW approval job.

## References

- Routing rules: [docs/routing/automerge-routing.md](../routing/automerge-routing.md)

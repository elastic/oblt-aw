# Workflow: `obs-aw-automerge.yml`

## Overview

Source file: [.github/workflows/obs-aw-automerge.yml](../../.github/workflows/obs-aw-automerge.yml)

This workflow runs for a **single** pull request from `github.event.pull_request` (`pull_request` trigger only). It validates the PR with `GITHUB_TOKEN`, runs the GH-AW mention-in-pr approval step when validation passes (ephemeral Vault-app token when `github-token-policy` is set), then runs **pascalgn/automerge-action** in the `automerge` job so the PR can squash-merge when labels, reviews, and checks satisfy configuration. If that merge attempt reports `merge_failed` or `not_ready` (for example when merge queue is required), the workflow runs `enable-merge-when-ready` to enable native GitHub auto-merge (`gh pr merge --auto --squash`) as a fallback. If the PR remains unmerged and auto-merge was not enabled, `report-automerge-outcome` fails the workflow and upserts a PR comment. Required status checks are **not** queried in `verify`; branch protection and merge readiness checks handle gating before merge.

Ingress selects which events dispatch here; see [Automerge routing](../routing/automerge-routing.md).

## Prerequisites

- Triggered via `workflow_call` from `trigger-obs-aw-automerge.yml` when prelude and route guards match author, `oblt-aw/ai/merge-ready`, and the right `pull_request` action.
- `github.event.pull_request` must be populated (same as dependency-review PR flows).

## Usage

Jobs:

- `verify`: shallow sparse checkout of `elastic/oblt-aw` (`allowed_pr_authors.json`, `validateAutomergePr.ts`, and npm manifests only), then runs `scripts/obs/validateAutomergePr.ts` for `github.event.pull_request.number` (author allow list aligned with dependency-review, merge-ready label, draft/fork/ref).
- `check-dependency-collection`: shallow sparse checkout of `elastic/oblt-aw` (collection config, gate scripts, and `package.json` / lockfile only), then classifies the PR by changed file paths against [config/obs/automerge-dependency-collections.json](../../config/obs/automerge-dependency-collections.json); skips `approve`/`automerge` when the collection is not enabled on the Control Plane Dashboard (`obs:automerge:<collection-id>` sub-features) and posts a PR comment explaining why (no extra labels in target repos). Prelude passes `shared-enabled-workflows` into this job.
- `approve`: invokes `elastic/ai-github-actions` `gh-aw-mention-in-pr.lock.yml` when `verify` and `check-dependency-collection` pass (Copilot must not call check-run APIs for gating; branch protection handles required checks at merge time). Passes `github-token-policy` from `shared-token-policy` so the nested lock mints an OIDC ephemeral token when non-empty; the approval is submitted as the Vault app identity and can satisfy CODEOWNERS when that app is listed for the changed paths. Empty policy keeps `GITHUB_TOKEN` (CODEOWNERS-required repos stay blocked until policy is set and the app is a code owner).
- `automerge`: runs **pascalgn/automerge-action** with `GITHUB_TOKEN` on the **same** repository as the PR (`PULL_REQUEST` is the PR number), after `approve`. Squash-merge when `MERGE_LABELS`, `MERGE_REQUIRED_APPROVALS`, and GitHub mergeability align with branch protection.
- `enable-merge-when-ready`: runs when `automerge` outputs `merge_failed` or `not_ready`; creates an ephemeral token via `elastic/oblt-actions/github/create-token@v1` and enables native auto-merge queue behavior with `gh pr merge --auto --squash`.
- `report-automerge-outcome`: after automerge (and optional fallback), succeeds when the PR was merged or native auto-merge is enabled; otherwise upserts a single PR comment (marker `obs-aw-automerge:outcome-gate`) explaining the blocker and fails the workflow so a successful conclusion cannot hide an unmerged PR.

There is no discover step. Prelude supplies **`allowed-pr-authors-csv`** into the `approve` job’s `oblt-aw-mention-in-pr` call. Merge-ready label and PR author gating remain in `validateAutomergePr.ts` and workflow `if` conditions; the canonical PR author list is [allowed_pr_authors.json](https://github.com/elastic/oblt-aw/blob/main/config/obs/allowed_pr_authors.json).

## Configuration

`GITHUB_TOKEN` follows least privilege: workflow root is `contents: read` only; each job sets the minimum scopes it needs.

| Job | Permissions |
|-----|-------------|
| Workflow (default) | `contents: read` |
| `verify` | `actions: read`, `contents: read`, `pull-requests: read` (validate script reads the PR) |
| `check-dependency-collection` | `contents: read`, `pull-requests: write` (list PR files, post or remove gate comment) |
| `approve` | `actions: read`, `contents: write`, `discussions: write`, `issues: write`, `pull-requests: write`, `id-token: write` (GH-AW mention-in-pr; OIDC mint when `github-token-policy` is set) |
| `automerge` | `contents: write`, `pull-requests: write` (automerge action merges the PR) |
| `enable-merge-when-ready` | `id-token: write` (required for ephemeral token minting before `gh pr merge --auto`) |
| `report-automerge-outcome` | `pull-requests: write` (upsert failure comment on the PR) |

### CODEOWNERS and ephemeral tokens

When `github-token-policy` is non-empty, `approve` mints an ephemeral token in the nested lock and submits the review as [elastic-vault-github-plugin-prod](https://github.com/apps/elastic-vault-github-plugin-prod). That single approval can clear “Require review from Code Owners” when the app is listed for the changed paths—no separate `codeowner-approve` job.

**Consumer requirement:** Whenever a repository (or path) requires a CODEOWNERS review for automerge to succeed, add the GitHub App [elastic-vault-github-plugin-prod](https://github.com/apps/elastic-vault-github-plugin-prod) as a code owner for those paths. Listing only a human team (for example `@elastic/observablt-ci`) is not enough—the app must appear in `CODEOWNERS` so its approval counts. Permissions alone do not satisfy CODEOWNERS. Empty `shared-token-policy` keeps `GITHUB_TOKEN` approval, which does not satisfy CODEOWNERS.

Example (alongside an existing team owner; use the app slug, not a team path):

```text
* @elastic/observablt-ci @elastic-vault-github-plugin-prod
```


## API / Interface

`workflow_call` contract:

- **Allow list:** `needs.run-aw-prelude.outputs.allowed-pr-authors-csv` for `gh-aw-mention-in-pr.lock.yml` (from [load-allowed-authors.yml](../../.github/workflows/load-allowed-authors.yml) via prelude).
- **Token policy:** `shared-token-policy` passed as `github-token-policy` into `gh-aw-mention-in-pr.lock.yml` (from `aw-prelude` / `workflow-token-policy`).

## References

- Routing rules: [docs/routing/automerge-routing.md](../routing/automerge-routing.md)

# Automerge Routing

## Overview

Client template: `trigger-obs-aw-automerge.yml` → `obs-aw-automerge.yml`

Routed workflow source: `.github/workflows/obs-aw-automerge.yml` (`verify`, `check-dependency-collection`, `approve`, `automerge`, conditional `enable-merge-when-ready`, and `report-automerge-outcome` on the PR). Merge first uses **pascalgn/automerge-action** with an ephemeral Vault-app token when `shared-token-policy` is set, otherwise `GITHUB_TOKEN`; when that step reports `merge_failed` or `not_ready`, the workflow retries a direct REST merge with the same token identity, then enables native GitHub auto-merge as a fallback. If the PR remains unmerged without auto-merge enabled, the workflow fails and upserts a PR comment.

## Usage

`obs-aw-automerge.yml` runs when prelude allows registry id `obs:automerge` (see `docs/workflows/aw-prelude.md`) and all of the following hold:

There is **no** `schedule` trigger for automerge. The reusable workflow uses `github.event.pull_request` from the caller (no PR discovery).

### `pull_request` events

- `github.event.action` is one of `opened`, `synchronize`, `reopened`, `labeled`
- Author is in the same allow list as dependency-review: `dependabot[bot]`, `renovate[bot]`, `Dependabot`, `Renovate`, `elastic-vault-github-plugin-prod[bot]`
- PR has label `oblt-aw/ai/merge-ready` at event time

The client template includes `labeled` in `pull_request` types (`trigger-obs-aw-automerge.yml`).

## Mandatory requirements evaluated at runtime

**`obs-aw-automerge.yml` — `verify` job** (`scripts/obs/validateAutomergePr.ts`):

| Requirement | Details |
|---------------|---------|
| Author | Same allow list as dependency-review (see above) |
| Label | `oblt-aw/ai/merge-ready` must be present on the PR |
| PR state | Not a draft |
| Branch origin | Upstream branch (head repo equals base repo — not a fork) |
| Refs | Head ref ≠ base ref |

**`obs-aw-automerge.yml` — `check-dependency-collection` job** (`scripts/obs/checkAutomergeDependencyCollection.ts`):

| Requirement | Details |
|---------------|---------|
| Classification | Changed file paths on the PR are matched against [config/obs/automerge-dependency-collections.json](../../config/obs/automerge-dependency-collections.json) (`file-glob` per collection). No extra labels are required in consumer repositories. |
| Enabled collections | Only collections enabled on the Control Plane Dashboard (`obs:automerge:<collection-id>` sub-feature checkboxes under Automerge) proceed to `approve` and `automerge`. The parent `obs:automerge` checkbox must also be enabled. |
| Skipped PRs | When classification fails or the collection is not enabled on the dashboard, the job posts or updates a single PR comment (marker `obs-aw-automerge:dependency-collection-gate`) and downstream jobs do not run. |

**`approve` job:** Nested `gh-aw-mention-in-pr` receives `github-token-policy` from prelude `shared-token-policy`. When non-empty, the lock mints an ephemeral Vault-app token and submits the review as that identity (satisfies required review **counts**; GitHub Apps cannot be CODEOWNERS). For repos with “Require review from Code Owners”, add the Vault app to classic branch-protection `pull_request_bypassers` and merge as that app (see [obs-aw-automerge.md](../workflows/obs-aw-automerge.md#codeowners-and-ephemeral-tokens)).

**`automerge` job** (after `approve`): When `shared-token-policy` is non-empty, mints a Vault-app token and runs **[pascalgn/automerge-action](https://github.com/pascalgn/automerge-action)** with it; when empty, uses `GITHUB_TOKEN`. The action enforces `MERGE_LABELS` (`oblt-aw/ai/merge-ready`), `MERGE_REQUIRED_APPROVALS`, fork/branch settings, and merges with **squash** when GitHub reports the PR as ready (required checks and reviews per branch protection and action config). Author and label gates are enforced in `verify` (`validateAutomergePr.ts`, same allow list as dependency-review).

**Required checks:** Validated by GitHub branch protection and the automerge action’s merge readiness logic, not by `validateAutomergePr.ts`.

## Merge strategy

Primary path: squash merge via **pascalgn/automerge-action** (Vault app when `shared-token-policy` is set, otherwise `GITHUB_TOKEN`) when the PR satisfies labels, approvals, and checks.

Fallback path: when `automerge` returns `merge_failed` or `not_ready` (for example with required merge queue), `enable-merge-when-ready` uses the same token choice, retries `PUT .../pulls/{n}/merge`, then runs `gh pr merge --auto --squash` to enqueue native GitHub auto-merge.

Outcome gate: `report-automerge-outcome` fails the workflow and upserts a single PR comment (marker `obs-aw-automerge:outcome-gate`) when the PR is still open and auto-merge was not enabled after the pipeline completes.

## Configuration

The routed workflow uses `GITHUB_TOKEN` with the permissions listed in `obs-aw-automerge.md`.

## References

- `docs/workflows/obs-aw-automerge.md`

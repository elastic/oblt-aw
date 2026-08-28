# Automerge Routing

## Overview

Client template: `trigger-obs-aw-automerge.yml` → `obs-aw-automerge.yml`

Routed workflow source: `.github/workflows/obs-aw-automerge.yml` (`verify`, `check-dependency-collection`, `approve`, conditional `codeowner-approve`, `automerge`, conditional `enable-merge-when-ready`, and `report-automerge-outcome` on the PR). Merge first uses **pascalgn/automerge-action** with `GITHUB_TOKEN`; when that step reports `merge_failed` or `not_ready`, the workflow enables native GitHub auto-merge as a fallback. If the PR remains unmerged without auto-merge enabled, the workflow fails and comments on the PR.

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

**`codeowner-approve` job** (after `approve`): When `reviewDecision` is still `REVIEW_REQUIRED` (for example CODEOWNERS still required after the agent’s `GITHUB_TOKEN` approval), mints an ephemeral token with the existing `shared-token-policy` and submits `gh pr review --approve` in the same job. Skips mint/approve when required reviews are already satisfied. Consumer repos that require CODEOWNERS review must list [elastic-vault-github-plugin-prod](https://github.com/apps/elastic-vault-github-plugin-prod) as a code owner for the relevant paths so that approval counts (see [obs-aw-automerge.md](../workflows/obs-aw-automerge.md#codeowners-and-ephemeral-tokens)).

**`automerge` job** (after `codeowner-approve`): **[pascalgn/automerge-action](https://github.com/pascalgn/automerge-action)** enforces `MERGE_LABELS` (`oblt-aw/ai/merge-ready`), `MERGE_REQUIRED_APPROVALS`, fork/branch settings, and merges with **squash** when GitHub reports the PR as ready (required checks and reviews per branch protection and action config). Author and label gates are enforced in `verify` (`validateAutomergePr.ts`, same allow list as dependency-review).

**Required checks:** Validated by GitHub branch protection and the automerge action’s merge readiness logic, not by `validateAutomergePr.ts`.

## Merge strategy

Primary path: squash merge via **pascalgn/automerge-action** when the PR satisfies labels, approvals, and checks.

Fallback path: when `automerge` returns `merge_failed` or `not_ready` (for example with required merge queue), `enable-merge-when-ready` mints an ephemeral token and runs `gh pr merge --auto --squash` to enqueue native GitHub auto-merge.

Outcome gate: `report-automerge-outcome` fails the workflow (with a PR comment) when the PR is still open and auto-merge was not enabled after the pipeline completes.

## Configuration

The routed workflow uses `GITHUB_TOKEN` with the permissions listed in `obs-aw-automerge.md`.

## References

- `docs/workflows/obs-aw-automerge.md`

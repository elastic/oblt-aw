# Automerge Routing

## Overview

Client template: `trigger-oblt-aw-automerge.yml` → `oblt-aw-automerge.yml`

Routed workflow source: `.github/workflows/oblt-aw-automerge.yml` (`verify`, `check-dependency-collection`, `approve`, `automerge`, and conditional `enable-merge-when-ready` on the PR). Merge first uses **pascalgn/automerge-action** with `GITHUB_TOKEN`; when that step reports `merge_failed`, the workflow enables native GitHub auto-merge as a fallback.

## Usage

`oblt-aw-automerge.yml` runs when prelude allows registry id `obs:automerge` (see `docs/workflows/aw-prelude.md`) and all of the following hold:

There is **no** `schedule` trigger for automerge. The reusable workflow uses `github.event.pull_request` from the caller (no PR discovery).

### `pull_request` events

- `github.event.action` is one of `opened`, `synchronize`, `reopened`, `labeled`
- Author is in the same allow list as dependency-review: `dependabot[bot]`, `renovate[bot]`, `Dependabot`, `Renovate`, `elastic-vault-github-plugin-prod[bot]`
- PR has label `oblt-aw/ai/merge-ready` at event time

The client template includes `labeled` in `pull_request` types (`trigger-oblt-aw-automerge.yml`).

## Mandatory requirements evaluated at runtime

**`oblt-aw-automerge.yml` — `verify` job** (`scripts/obs/validateAutomergePr.ts`):

| Requirement | Details |
|---------------|---------|
| Author | Same allow list as dependency-review (see above) |
| Label | `oblt-aw/ai/merge-ready` must be present on the PR |
| PR state | Not a draft |
| Branch origin | Upstream branch (head repo equals base repo — not a fork) |
| Refs | Head ref ≠ base ref |

**`oblt-aw-automerge.yml` — `check-dependency-collection` job** (`scripts/obs/checkAutomergeDependencyCollection.ts`):

| Requirement | Details |
|---------------|---------|
| Classification | Changed file paths on the PR are matched against [config/obs/automerge-dependency-collections.json](../../config/obs/automerge-dependency-collections.json) (`file-glob` per collection). No extra labels are required in consumer repositories. |
| Active collections | Only collections with `"active": true` proceed to `approve` and `automerge`. |
| Skipped PRs | When classification fails or the collection is inactive, the job posts or updates a single PR comment (marker `oblt-aw-automerge:dependency-collection-gate`) and downstream jobs do not run. |

**`automerge` job** (after approval): **[pascalgn/automerge-action](https://github.com/pascalgn/automerge-action)** enforces `MERGE_LABELS` (`oblt-aw/ai/merge-ready`), `MERGE_REQUIRED_APPROVALS`, fork/branch settings, and merges with **squash** when GitHub reports the PR as ready (required checks and reviews per branch protection and action config). Author and label gates are enforced in `verify` (`validateAutomergePr.ts`, same allow list as dependency-review).

**Required checks:** Validated by GitHub branch protection and the automerge action’s merge readiness logic, not by `validateAutomergePr.ts`.

## Merge strategy

Primary path: squash merge via **pascalgn/automerge-action** when the PR satisfies labels, approvals, and checks.

Fallback path: when `automerge` returns `merge_failed` (for example with required merge queue), `enable-merge-when-ready` mints an ephemeral token and runs `gh pr merge --auto --squash` to enqueue native GitHub auto-merge.

## Configuration

The routed workflow uses `GITHUB_TOKEN` with the permissions listed in `oblt-aw-automerge.md`.

## References

- `docs/workflows/oblt-aw-automerge.md`

# Automerge Routing

## Overview

Entrypoint source: `.github/workflows/oblt-aw-ingress.yml`

Routed workflow source: `.github/workflows/gh-aw-automerge.yml` (verify and approve on the PR). Merge runs in `.github/workflows/automerge.yml` via `workflow_dispatch` (triggered with `gh workflow run`) so it is not attached as a long-running check on the PR head commit.

## Usage

Ingress dispatches to `gh-aw-automerge.yml` when the Control Plane dashboard gate allows registry id `automerge` (see `docs/workflows/oblt-aw-ingress.md` — `get-enabled-workflows` / `enabled-workflows`) and all of the following hold:

There is **no** `schedule` trigger for automerge. The reusable workflow uses `github.event.pull_request` from the caller (no PR discovery).

### `pull_request` events

- `github.event.action` is one of `opened`, `synchronize`, `reopened`, `labeled`
- Author is in the same allow list as dependency-review: `dependabot[bot]`, `renovate[bot]`, `Dependabot`, `Renovate`, `elastic-vault-github-plugin-prod[bot]`
- PR has label `oblt-aw/ai/merge-ready` at event time

The client entrypoint must include `labeled` in `pull_request` types (see the distributed `oblt-aw.yml` template).

## Mandatory requirements evaluated at runtime

**`gh-aw-automerge.yml` — `verify` job** (`scripts/validateAutomergePr.ts`):

| Requirement | Details |
|---------------|---------|
| Author | Same allow list as dependency-review (see above) |
| Label | `oblt-aw/ai/merge-ready` must be present on the PR |
| PR state | Not a draft |
| Branch origin | Upstream branch (head repo equals base repo — not a fork) |
| Refs | Head ref ≠ base ref |

**[`automerge.yml`](../../.github/workflows/automerge.yml)** (after approval): re-checks author via `load-allowed-pr-authors` output (from `config/allowed_pr_authors.json`), then **[pascalgn/automerge-action](https://github.com/pascalgn/automerge-action)** enforces `MERGE_LABELS` (`oblt-aw/ai/merge-ready`), `MERGE_REQUIRED_APPROVALS`, fork/branch settings, and merges with **squash** when GitHub reports the PR as ready (required checks and reviews per branch protection and action config).

**Required checks:** Validated by GitHub branch protection and the automerge action’s merge readiness logic, not by `validateAutomergePr.ts`.

## Merge strategy

Squash merge via **pascalgn/automerge-action** when the PR satisfies labels, approvals, and checks. This is distinct from GraphQL `enablePullRequestAutoMerge` (native auto-merge queue).

## Configuration

The routed workflow uses `GITHUB_TOKEN` with the permissions listed in `gh-aw-automerge.md`. `COPILOT_GITHUB_TOKEN` is required for the approval job.

## References

- `docs/workflows/gh-aw-automerge.md`

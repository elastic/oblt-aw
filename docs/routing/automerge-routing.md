# Automerge Routing

## Overview

Entrypoint source: `.github/workflows/oblt-aw-ingress.yml`

Routed workflow source: `.github/workflows/gh-aw-automerge.yml`

## Usage

Ingress dispatches to `gh-aw-automerge.yml` when the Control Plane dashboard gate allows registry id `automerge` (see `docs/workflows/oblt-aw-ingress.md` — `get-enabled-workflows` / `enabled-workflows`) and all of the following hold:

There is **no** `schedule` trigger for automerge. The reusable workflow uses `github.event.pull_request` from the caller (no PR discovery).

### `pull_request` events

- `github.event.action` is one of `opened`, `synchronize`, `reopened`, `labeled`
- Author is in the same allow list as dependency-review: `dependabot[bot]`, `renovate[bot]`, `Dependabot`, `Renovate`, `elastic-vault-github-plugin-prod[bot]`
- PR has label `oblt-aw/ai/merge-ready` at event time

The client entrypoint must include `labeled` in `pull_request` types (see the distributed `oblt-aw.yml` template).

## Mandatory requirements evaluated at runtime

`scripts/validateAutomergePr.ts` and `enableAutomergeForApprovedPr.ts` enforce:

| Requirement | Details |
|---------------|---------|
| Author | Same allow list as dependency-review (see above) |
| Label | `oblt-aw/ai/merge-ready` must be present on the PR |
| PR state | Not a draft |
| Branch origin | Upstream branch (head repo equals base repo — not a fork) |
| Refs | Head ref ≠ base ref |
| Approved by | `github-actions[bot]` before auto-merge is enabled |

**Required checks:** Not validated in these scripts. After auto-merge is enabled, GitHub waits for branch protection / merge requirements before merging.

## Merge strategy

Automerge is enabled using GraphQL `enablePullRequestAutoMerge` with **squash**. GitHub merges when branch protection is satisfied.

## Configuration

The routed workflow uses `GITHUB_TOKEN` with the permissions listed in `gh-aw-automerge.md`. `COPILOT_GITHUB_TOKEN` is required for the approval job.

## References

- `docs/workflows/gh-aw-automerge.md`

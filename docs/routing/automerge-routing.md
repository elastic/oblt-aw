# Automerge Routing

## Overview

Entrypoint source: `.github/workflows/oblt-aw-ingress.yml`

Routed workflow source: `.github/workflows/gh-aw-automerge.yml`

## Usage

Ingress dispatches to `gh-aw-automerge.yml` when **any** of the following is true, and the Control Plane dashboard gate allows registry id `automerge` (see `docs/workflows/oblt-aw-ingress.md` — `get-enabled-workflows` / `enabled-workflows`).

There is **no** `schedule` trigger for automerge. The reusable workflow always targets **`github.event.pull_request.number`** (no PR discovery).

**Ingress preconditions** (same PR author allow list as dependency-review):

- `dependabot[bot]`, `renovate[bot]`, `Dependabot`, `Renovate`, `elastic-vault-github-plugin-prod[bot]`

**Ingress preconditions** (label on the PR at event time):

- `contains(join(github.event.pull_request.labels.*.name, ','), 'oblt-aw/ai/merge-ready')`

### Pull request events

- `github.event_name == 'pull_request'`
- `github.event.action` is one of `opened`, `synchronize`, `reopened`, `labeled`

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
| Checks | All check-runs complete with conclusion `success`, `skipped`, or `neutral` (via `GITHUB_TOKEN` / Checks API before Copilot) |
| Approved by | `github-actions[bot]` before auto-merge is enabled |

## Merge strategy

Automerge is enabled using GraphQL `enablePullRequestAutoMerge` with **squash**. GitHub merges when branch protection is satisfied.

## Configuration

The routed workflow uses `GITHUB_TOKEN` with the permissions listed in `gh-aw-automerge.md`. `COPILOT_GITHUB_TOKEN` is required for the approval job.

## References

- `docs/workflows/gh-aw-automerge.md`

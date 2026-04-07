# Automerge Routing

## Overview

Entrypoint source: `.github/workflows/oblt-aw-ingress.yml`

Routed workflow source: `.github/workflows/gh-aw-automerge.yml`

## Usage

Ingress dispatches to `gh-aw-automerge.yml` when **any** of the following is true, and the Control Plane dashboard gate allows registry id `automerge` (see `docs/workflows/oblt-aw-ingress.md` — `get-enabled-workflows` / `enabled-workflows`):

### Scheduled scan

- `github.event_name == 'schedule'`

The workflow scans **all open PRs** in the consumer repository and enables automerge on every PR that satisfies all mandatory requirements.

### PR lifecycle event

- `github.event_name == 'pull_request'`
- `github.event.action` is one of `opened`, `synchronize`, `reopened`
- `github.event.pull_request.user.login` is `elastic-vault-github-plugin-prod[bot]`

Allows the workflow to react immediately when a qualifying PR is opened or updated.

### Approval event

- `github.event_name == 'pull_request_review'`
- `github.event.action == 'submitted'`
- `github.event.review.state == 'approved'`
- `github.event.pull_request.user.login` is `elastic-vault-github-plugin-prod[bot]`

Allows the workflow to react immediately when a qualifying PR receives the expected approval.

## Mandatory requirements evaluated at runtime

All of the following must be true for a PR to have automerge enabled:

| Requirement | Details |
|---------------|---------|
| Author | `elastic-vault-github-plugin-prod[bot]` |
| Label | `oblt-aw/ai/merge-ready` must be present |
| PR state | Not a draft |
| Branch origin | Upstream branch (head repo equals base repo — not a fork) |
| Checks | All completed check-runs must have conclusion `success`, `skipped`, or `neutral` |
| Approved by | `github-actions[bot]` (default `GITHUB_TOKEN` actor) |

## Merge strategy

Automerge is enabled using `gh pr merge --auto --squash`. The merge is performed by GitHub as soon as all branch-protection rules are satisfied in the consumer repository.

## Configuration

The routed workflow uses the default `GITHUB_TOKEN` with `pull-requests: write`. No additional secrets are required.

## References

- `docs/workflows/gh-aw-automerge.md`

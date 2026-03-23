# Automerge routing

This folder documents routing and conventions for the automerge workflow.

## Entrypoint routes

`oblt-aw-ingress.yml` dispatches to `gh-aw-automerge.yml` when **any** of the following conditions is true:

### Scheduled scan
- event is `schedule`

The workflow scans **all open PRs** in the consumer repository and enables automerge on every PR that satisfies all mandatory requirements.

### PR lifecycle event
- event is `pull_request`
- action is one of `opened`, `synchronize`, `reopened`
- PR author is `elastic-vault-github-plugin-prod[bot]`

Allows the workflow to react immediately when a qualifying PR is opened or updated.

### Approval event
- event is `pull_request_review`
- action is `submitted`
- review state is `approved`
- PR author is `elastic-vault-github-plugin-prod[bot]`

Allows the workflow to react immediately when a qualifying PR receives the expected approval.

## Mandatory requirements evaluated at runtime

All of the following must be true for a PR to have automerge enabled:

| Requirement | Details |
|---|---|
| Author | `elastic-vault-github-plugin-prod[bot]` |
| Label | `oblt-aw/ai/merge-ready` must be present |
| PR state | Not a draft |
| Branch origin | Upstream branch (head repo equals base repo — not a fork) |
| Checks | All completed check-runs must have conclusion `success`, `skipped`, or `neutral` |
| Approved by | `github-actions[bot]` (default `GITHUB_TOKEN` actor) |

## Merge strategy

Automerge is enabled using `gh pr merge --auto --squash`. The merge is performed by GitHub as soon as all branch-protection rules are satisfied in the consumer repository.

## Permissions required

Both `gh-aw-automerge.yml` and `gh-aw-automerge-approve.yml` use the default `GITHUB_TOKEN` with the following scopes:

| Scope | Level |
|---|---|
| `actions` | `read` |
| `checks` | `read` |
| `contents` | `write` |
| `discussions` | `write` |
| `issues` | `write` |
| `pull-requests` | `write` |

No additional secrets are required.

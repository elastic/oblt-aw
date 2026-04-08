# Automerge Routing

## Overview

Entrypoint source: `.github/workflows/oblt-aw-ingress.yml`

Routed workflow source: `.github/workflows/gh-aw-automerge.yml`

## Usage

Ingress dispatches to `gh-aw-automerge.yml` when **any** of the following is true, and the Control Plane dashboard gate allows registry id `automerge` (see `docs/workflows/oblt-aw-ingress.md` — `get-enabled-workflows` / `enabled-workflows`).

There is **no** `schedule` trigger for automerge. The reusable workflow receives the PR number via the `pull-request-number` `workflow_call` input (no PR discovery).

### Path A — `pull_request` events

- `github.event.action` is one of `opened`, `synchronize`, `reopened`, `labeled`
- Author is in the same allow list as dependency-review: `dependabot[bot]`, `renovate[bot]`, `Dependabot`, `Renovate`, `elastic-vault-github-plugin-prod[bot]`
- PR has label `oblt-aw/ai/merge-ready` at event time

The client entrypoint must include `labeled` in `pull_request` types (see the distributed `oblt-aw.yml` template).

### Path B — `check_run` events (`completed`)

Re-runs automerge when **another** check on the PR finishes so eligibility is re-evaluated after CI (and similar) without a new push.

- `join(github.event.check_run.pull_requests.*.number, ',')` is non-empty (check is associated with at least one PR).
- The completed check’s `name` is **not** one of the oblt-aw self-triggers (current Elastic defaults): not starting with `Automerge /`, and not `Observability Agentic Workflow Ingress / automerge`, `Observability Agentic Workflow Ingress / dashboard-enabled-workflows`, or `Observability Agentic Workflow Entrypoint / run-aw`. If you rename the distributed entrypoint workflow or those jobs, update these exclusions in `oblt-aw-ingress.yml` to match.

Author, merge-ready label, and the rest are enforced in `validateAutomergePr.ts` (which fetches the PR); Path B may invoke that script more often for PRs that are not bot merge-ready candidates — `verify` exits quickly.

## Mandatory requirements evaluated at runtime

`scripts/validateAutomergePr.ts` and `enableAutomergeForApprovedPr.ts` enforce:

| Requirement | Details |
|---------------|---------|
| Author | Same allow list as dependency-review (see above) |
| Label | `oblt-aw/ai/merge-ready` must be present on the PR |
| PR state | Not a draft |
| Branch origin | Upstream branch (head repo equals base repo — not a fork) |
| Refs | Head ref ≠ base ref |
| Checks | All **other** check-runs on the head SHA complete with conclusion `success`, `skipped`, or `neutral`. Check runs for the **current** workflow run (same `run_id` in `details_url`) are ignored so the automerge job does not wait on itself. When remaining checks finish, ingress runs again on `check_run` `completed` (Path B) or on a matching `pull_request` event. |
| Approved by | `github-actions[bot]` before auto-merge is enabled |

## Merge strategy

Automerge is enabled using GraphQL `enablePullRequestAutoMerge` with **squash**. GitHub merges when branch protection is satisfied.

## Configuration

The routed workflow uses `GITHUB_TOKEN` with the permissions listed in `gh-aw-automerge.md`. `COPILOT_GITHUB_TOKEN` is required for the approval job.

## References

- `docs/workflows/gh-aw-automerge.md`

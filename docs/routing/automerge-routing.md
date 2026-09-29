# Automerge Routing

## Overview

Client template chains:

- `trigger-obs-aw-pull-request.yml` → `obs-aw-event-pull-request.yml` → `obs-aw-automerge.yml` (validate, approve, try merge, **arm** if checks pending)
- `trigger-obs-aw-status.yml` → `obs-aw-event-status.yml` → `obs-aw-automerge-complete.yml` (on Buildkite **success**: Vault REST merge for armed PRs)

For the user-facing Automerge service catalogue, see [Automerge services](../guides/user/automerge-services.md).

Routed workflow sources:

- `.github/workflows/obs-aw-automerge.yml` — PR path (`verify`, `check-dependency-collection`, `approve`, `automerge`, `arm-for-status-complete`, `report-automerge-outcome`)
- `.github/workflows/obs-aw-automerge-complete.yml` — status-success path (`discover`, `verify`, `check-dependency-collection`, `merge`)

**Approve (PR path):** Nested `gh-aw-mention-in-pr` picks a token so the approver is never the PR author (GitHub rejects self-APPROVE). Default is empty `github-token-policy` → `GITHUB_TOKEN` / `github-actions[bot]`. When the author is `github-actions[bot]`, pass `shared-token-policy` so Vault submits the review. Author allow list is **only** [allowed_pr_authors.json](../../config/obs/allowed_pr_authors.json).

**Merge strategy (CI-duration independent):**

1. **PR path** tries a short squash-merge (pascalgn + one REST retry).
2. If checks are still pending → upsert armed comment (`<!-- obs-aw-automerge:armed -->`). Outcome success = merged **or** armed. Native `--auto` is soft-only (does not count as success; async `--auto` ignores Vault bypassers).
3. **Status path** on Buildkite `status` success finds an armed merge-ready PR for `github.event.sha` and squash-merges via REST as the Vault app so classic `pull_request_bypassers` apply.

## Usage

Both workflows require prelude to allow registry id `obs:automerge` (see `docs/workflows/aw-prelude.md`).

There is **no** `schedule` trigger for automerge.

### `pull_request` events

- `github.event.action` is one of `opened`, `synchronize`, `reopened`, `labeled`
- Author is in the same allow list as dependency-review
- PR has label `oblt-aw/ai/merge-ready` at event time

### `status` events (complete)

- `github.event.state == 'success'`
- `github.event.context` contains `buildkite`
- Open PR for `github.event.sha` with `oblt-aw/ai/merge-ready` **and** armed comment marker

## Mandatory requirements evaluated at runtime

**`obs-aw-automerge.yml` / `obs-aw-automerge-complete.yml` — `verify`** (`scripts/obs/validateAutomergePr.ts`):

| Requirement | Details |
|---------------|---------|
| Author | Same allow list as dependency-review ([allowed_pr_authors.json](../../config/obs/allowed_pr_authors.json)); GraphQL `app/<slug>` is normalized to `<slug>[bot]` before matching |
| Token policy | Non-empty `shared-token-policy` required when author is `github-actions[bot]` |
| Label | `oblt-aw/ai/merge-ready` must be present on the PR |
| PR state | Not a draft |
| Branch origin | Upstream branch (head repo equals base repo — not a fork) |
| Refs | Head ref ≠ base ref |

**Collection gate** (`scripts/obs/checkAutomergeDependencyCollection.ts`): unchanged — path classification + dashboard `obs:automerge:<collection-id>` enablement.

**Status discover** (`scripts/obs/automergeArmed.ts`): requires armed marker from the PR path so approve has already run before completion.

## Configuration

The routed workflows use `GITHUB_TOKEN` with the permissions listed in `obs-aw-automerge.md` and `obs-aw-automerge-complete.md`.

Client `trigger-obs-aw-status.yml` needs `contents: write` on the entrypoint job (union includes automerge-complete merge).

## References

- `docs/workflows/obs-aw-automerge.md`
- `docs/workflows/obs-aw-automerge-complete.md`
- `docs/workflows/obs-aw-client-template.md`

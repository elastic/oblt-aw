# Automerge Routing

## Overview

Client template chains:

- `trigger-obs-aw-pull-request.yml` → `obs-aw-event-pull-request.yml` → `obs-aw-automerge.yml` (validate, approve, try merge, **arm** if checks pending)
- `trigger-obs-aw-schedule-frequent.yml` → `obs-aw-event-schedule.yml` (`schedule-profile: frequent`) → `obs-aw-automerge-deferred.yml` (Vault REST merge for armed PRs)

For the user-facing Automerge service catalogue, see [Automerge services](../guides/user/automerge-services.md).

Routed workflow sources:

- `.github/workflows/obs-aw-automerge.yml` — PR path (`verify`, `check-dependency-collection`, `approve`, `automerge`, `arm-for-deferred-merge`, `report-automerge-outcome`)
- `.github/workflows/obs-aw-automerge-deferred.yml` — frequent schedule profile (`discover`, matrix `merge`)

**Approve (PR path):** Nested `gh-aw-mention-in-pr` picks a token so the approver is never the PR author (GitHub rejects self-APPROVE). Default is empty `github-token-policy` → `GITHUB_TOKEN` / `github-actions[bot]`. When the author is `github-actions[bot]`, pass `shared-token-policy` so Vault submits the review. Author allow list is **only** [allowed_pr_authors.json](../../config/obs/allowed_pr_authors.json).

**Merge strategy (CI-duration independent):**

1. **PR path** tries a short squash-merge (pascalgn + one REST retry).
2. If checks are still pending → upsert armed comment (`<!-- obs-aw-automerge:armed -->`). Outcome success = merged, armed, or soft-succeed on `not_ready`.
3. **Frequent schedule profile** (client cron every 30 minutes) lists all open armed merge-ready PRs and retries REST merge as the Vault app so classic `pull_request_bypassers` apply (honored only on direct REST merge as that app — not by async `--auto` / merge-queue completion).

Required checks are enforced by GitHub’s merge API on every attempt — this automation only chooses **when** to wake up. There is **no** Buildkite status-success route for automerge (status stays ESTC-failure only).

## Usage

Both workflows require prelude to allow registry id `obs:automerge` (see `docs/workflows/aw-prelude.md`).

### `pull_request` events

- `github.event.action` is one of `opened`, `synchronize`, `reopened`, `labeled`
- Author is in the same allow list as dependency-review
- PR has label `oblt-aw/ai/merge-ready` at event time

### `schedule` / `workflow_dispatch` (deferred merge)

- Client cron or manual dispatch of `trigger-obs-aw-schedule-frequent.yml` (`schedule-profile: frequent`)
- Open PRs with `oblt-aw/ai/merge-ready` **and** armed comment marker
- No-op when none are armed (discover exits without matrix work)

## Mandatory requirements evaluated at runtime

**`obs-aw-automerge.yml` / `obs-aw-automerge-deferred.yml` — verify** (`scripts/obs/validateAutomergePr.ts`):

| Requirement | Details |
|---------------|---------|
| Author | Same allow list as dependency-review ([allowed_pr_authors.json](../../config/obs/allowed_pr_authors.json)); GraphQL `app/<slug>` is normalized to `<slug>[bot]` before matching |
| Token policy | Non-empty `shared-token-policy` required when author is `github-actions[bot]` |
| Label | `oblt-aw/ai/merge-ready` must be present on the PR |
| PR state | Not a draft |
| Branch origin | Upstream branch (head repo equals base repo — not a fork) |
| Refs | Head ref ≠ base ref |

**Collection gate** (`scripts/obs/checkAutomergeDependencyCollection.ts`):

| Requirement | Details |
|---------------|---------|
| Classification | Changed file paths on the PR are matched against [config/obs/automerge-dependency-collections.json](../../config/obs/automerge-dependency-collections.json) (`file-glob` per collection). No extra labels are required in consumer repositories. |
| Enabled collections | Only collections enabled on the Control Plane Dashboard (`obs:automerge:<collection-id>` sub-feature checkboxes under Automerge) proceed to `approve` and `automerge`. The parent `obs:automerge` checkbox must also be enabled. |
| Skipped PRs | When classification fails or the collection is not enabled on the dashboard, the job posts or updates a single PR comment (marker `obs-aw-automerge:dependency-collection-gate`) and downstream jobs do not run. |

**`approve` job:** Nested `gh-aw-mention-in-pr` uses author-aware `github-token-policy` (Vault only for `github-actions[bot]` authors; otherwise `GITHUB_TOKEN`). For repos with “Require review from Code Owners”, add the Vault app to classic branch-protection `pull_request_bypassers` and merge as that app (see [obs-aw-automerge.md](../workflows/obs-aw-automerge.md#codeowners-and-ephemeral-tokens)).

**Deferred discover** (`scripts/obs/discover_armed_automerge_prs.sh`): requires armed marker from the PR path so approve has already run before the deferred merge.

**Required checks:** Validated by GitHub’s merge API on every PR-path and deferred-merge attempt, not by `validateAutomergePr.ts`.

## Configuration

The routed workflows use `GITHUB_TOKEN` with the permissions listed in `obs-aw-automerge.md` and `obs-aw-automerge-deferred.md`.

Client `trigger-obs-aw-schedule-frequent.yml` needs `contents: write` on the entrypoint job (union includes automerge-deferred merge).

## References

- `docs/workflows/obs-aw-automerge.md`
- `docs/workflows/obs-aw-automerge-deferred.md`
- `docs/workflows/obs-aw-client-template.md`

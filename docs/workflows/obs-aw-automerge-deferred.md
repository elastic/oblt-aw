# Workflow: `obs-aw-automerge-deferred.yml`

## Overview

Source file: [.github/workflows/obs-aw-automerge-deferred.yml](../../.github/workflows/obs-aw-automerge-deferred.yml)

Deferred merge path for [obs-aw-automerge.yml](obs-aw-automerge.md). Finds open PRs that already have `oblt-aw/ai/merge-ready` and the armed comment marker (`<!-- obs-aw-automerge:armed -->`), re-checks author/collection gates, and squash-merges via the REST API as the Vault app when `shared-token-policy` is set.

**Single wake-up:** the frequent schedule client `trigger-obs-aw-schedule-frequent.yml` (`schedule-profile: frequent` on `obs-aw-event-schedule.yml`; cron every 30 minutes + `workflow_dispatch`). It does **not** listen to Buildkite `status` success, `check_run`, or `check_suite` (those multiply CI cost). GitHub’s merge API still enforces **all** required checks on each attempt.

## Prerequisites

- Client `trigger-obs-aw-schedule-frequent.yml` must be installed (distribution).
- Prelude allows registry id `obs:automerge` (same dashboard gate as the PR automerge path).
- The PR was previously armed by `obs-aw-automerge.yml` after approve.

## Usage

Jobs:

- `discover`: list open armed merge-ready PRs (`scripts/obs/discover_armed_automerge_prs.sh`). No-op when none match.
- `merge` (matrix per candidate): `validateAutomergePr.ts`, collection gate, then Vault (or `GITHUB_TOKEN`) REST squash-merge via `gh api` pinned to head SHA. Pending-check / already-merged responses exit success (the next frequent schedule tick may merge later); other failures fail that matrix cell.

## Configuration

| Job | Permissions |
|-----|-------------|
| Workflow (default) | `contents: read` |
| `discover` | `contents: read`, `pull-requests: read` |
| `merge` | `actions: read`, `contents: write`, `pull-requests: write`, `id-token: write` |

## References

- [Automerge routing](../routing/automerge-routing.md)
- [obs-aw-automerge.md](obs-aw-automerge.md)
- [Client templates](obs-aw-client-template.md)

# Workflow: `obs-aw-automerge-complete.yml`

## Overview

Source file: [.github/workflows/obs-aw-automerge-complete.yml](../../.github/workflows/obs-aw-automerge-complete.yml)

Status-triggered completion for [obs-aw-automerge.yml](obs-aw-automerge.md). When a Buildkite commit status becomes **success**, this workflow finds an open PR for that SHA that already has `oblt-aw/ai/merge-ready` and the armed comment marker (`<!-- obs-aw-automerge:armed -->`), re-checks author/collection gates, and squash-merges via the REST API as the Vault app when `shared-token-policy` is set.

This path is **independent of CI duration**: the PR path arms while checks are pending; this workflow merges when GitHub emits the success status.

## Prerequisites

- Client `trigger-obs-aw-status.yml` must run on Buildkite `status` **success** (as well as failure for ESTC).
- Prelude allows registry id `obs:automerge` (same dashboard gate as the PR automerge path).
- The PR was previously armed by `obs-aw-automerge.yml` after approve.

## Usage

Jobs:

- `discover`: maps `github.event.sha` → open armed merge-ready PR (`scripts/obs/automergeArmed.ts`). No-op when none match.
- `verify`: same `validateAutomergePr.ts` gates as the PR path.
- `check-dependency-collection`: same collection enablement gate as the PR path.
- `merge`: Vault (or `GITHUB_TOKEN`) REST squash-merge pinned to the discovered head SHA (`scripts/obs/mergeAutomergePrRest.ts`). `pending_checks` exits success (another status may complete later); other failures fail the job.

## Configuration

| Job | Permissions |
|-----|-------------|
| Workflow (default) | `contents: read` |
| `discover` | `contents: read`, `pull-requests: read` |
| `verify` | `actions: read`, `contents: read`, `pull-requests: read` |
| `check-dependency-collection` | `contents: read`, `pull-requests: write` |
| `merge` | `contents: write`, `pull-requests: write`, `id-token: write` |

## References

- [Automerge routing](../routing/automerge-routing.md)
- [obs-aw-automerge.md](obs-aw-automerge.md)

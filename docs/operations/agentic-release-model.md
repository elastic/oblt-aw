# Agentic workflow release model

**Status:** Implementation for [#1878](https://github.com/elastic/oblt-aw/issues/1878) (parent [#1879](https://github.com/elastic/oblt-aw/issues/1879)).
**Testing contract:** [agentic-workflow-testing-platform](../architecture/agentic-workflow-testing-platform.md).

## Goal

Promote control-plane changes safely with mandatory gating E2E, keep consumer trigger churn low (major bumps only), and support quick rollback.

## Current pins (inventory)

| Surface | Location | Pointer today |
|---------|----------|---------------|
| Distributed client triggers | `.github/remote-workflow-template/**/trigger-*-aw-*.yml` | `elastic/oblt-aw/.../obs-aw-event-*.yml@main` until first promote creates `v0` / `v0.0.0`, then a follow-up PR switches the shared train to `@v0` |
| Installed client triggers (incl. control plane) | `.github/workflows/trigger-*-aw-*.yml` in each active repo | Same files distribute installs from the remote templates; `elastic/oblt-aw` is a pilot target |
| Pilot / guinea-pig pins | Selected active repos (at least `elastic/oblt-aw`) | Stay on `@main` for early failure detection after the shared train moves to `@v0` (pin policy TBD when `@v0` lands) |
| E2E-only schedule entry | `.github/workflows/e2e-trigger-obs-aw-schedule.yml` | Relative `./` (control-plane only; not distributed) |
| Event orchestrators → routes | `obs-aw-event-*.yml` | Relative `./` (inherits caller pin) |
| In-repo GH-AW locks | `obs-aw-autodoc.yml`, `obs-aw-dependency-review.yml`, `obs-aw-estc-pr-buildkite-detective.yml` | Relative `./gh-aw-*.lock.yml` (inherits caller pin) |
| Upstream locks still in `ai-github-actions` | Other `obs-aw-*.yml` wrappers | `elastic/ai-github-actions/...@main` (until [#1876](https://github.com/elastic/oblt-aw/issues/1876)) |
| Release metadata | `config/release-pointers.json` | `current` / `next` / `previous` SHAs + semver |

**Why pilots stay on `@main`:** After promote, most consumers pin `@v0`. Pilot repositories (including `elastic/oblt-aw`) keep consuming tip of `main` so live schedules, PR routes, and E2E that poll real client triggers catch control-plane regressions before the shared train promotes.

## Target model (hybrid)

- **Shared train (default):** one moving major tag `v0` for all distributed clients while the promote train is proven (templates pin `@v0` only after the tag exists).
- **Immutable audit tags:** `v0.x.y` created on each promote (never moved).
- **Moving ops tags:** `v0` (current), `next`, `previous`.
- **Graduation:** when the process is fully automated and testable, promote `major` → `v1.0.0`, bump templates to `@v1`, and redistribute.
- **Opt-in fine grain:** per-workflow pointers only when a route must promote independently (not implemented in the first slice; extend `release-pointers.json` when needed).

```mermaid
flowchart LR
  Main[Merge to main]
  Promo[Promote on main: E2E then tag]
  Main --> Promo
  Promo -->|rollback| Prev[Retarget vN to previous]
```

### Consumer churn

| Change type | Consumer action |
|-------------|-----------------|
| Patch / minor (compatible) | None — retarget `v0` after promote (once consumers pin `@v0`) |
| Major / breaking (incl. graduate to `v1`) | Bump templates to `@v1` (or next major), redistribute |

## Automation vs human gates

| Step | Mode |
|------|------|
| Merge to `main` | Automated CI (unit, functional, integration) |
| Promote (`aw-release-promote.yml`) | Manual `workflow_dispatch` on `main` with `release-type` (`patch` / `minor` / `major`); calls `e2e-all` then tags the gated SHA and creates a GitHub Release |
| Rollback (`aw-release-rollback.yml`) | Manual; confirm input must be `rollback` |
| Major bump / model or security-sensitive changes | Human review before promote |

## Promote contract

1. Dispatch `aw-release-promote.yml` **on the default branch** (`main`).
2. Choose `release-type`: `patch`, `minor`, or `major`. First promote (empty current pointer) always creates `v0.0.0` from `config/release-pointers.json` `major`.
3. Workflow calls `e2e-all` with `checkout-ref` set to `github.sha` (tip of `main` at promote start). Harness/oracle code is pinned to that SHA; live routes on pilot repos (including `elastic/oblt-aw`) exercise **default-branch tip** via `@main` client pins (and relative `e2e-trigger-*` where used).
4. Before mutating tags, re-fetch and require the promote SHA is an **ancestor of** `origin/main` (or still the tip). If `main` advanced during E2E, promote **continues** and tags the gated SHA.
5. On success: create immutable `vX.Y.Z` (no force-push), move `vX` / `next` / `previous`, **land** `config/release-pointers.json` via a Vault-authored PR (org Require-a-PR blocks direct pushes to `main`; approve as `GITHUB_TOKEN`, squash-merge as Vault), push tags, then create a **GitHub Release** for `vX.Y.Z` with auto-generated notes (range from the prior immutable semver when present). Semver bumps from the **highest** pointer semver so rollback cannot rewind immutable numbering. Before opening the pointers PR, fail closed if tip’s `release-pointers.json` differs from the plan-base SHA (re-dispatch on current tip; do not overwrite a newer promote/rollback landing).

Standalone `e2e-all.yml` remains available for smoke without tagging (`checkout-ref` defaults to `main`). Manual `workflow_dispatch` must run from the default branch; `checkout-ref` may only be that tip or a full SHA on its history. Promote pins `github.sha` at dispatch. PR CI does not call live E2E.

## Quick rollback

| Item | Value |
|------|-------|
| Action | `aw-release-rollback.yml` on default branch only (confirm=`rollback`) |
| Effect | Retarget current `tags.current` (`vN`) + `next` to `previous` SHA; swap pointers |
| Semver after rollback | `current` shows the restored release; next promote bumps from max(pointer semvers) |
| Cross-major | After a major promote, rollback moves the **new** major tag (`v1`, …), not the prior major |
| Who | Maintainers with Actions `workflow_dispatch` on this repo |
| Recovery target | **≤ 15 minutes** when git tags and `release-pointers.json` are healthy |
| Optional blast-radius stop | Disable routes via Control Plane Dashboard ([aw-prelude](../workflows/aw-prelude.md)) |

## First promote (after this model lands)

1. Merge the release-model PR to `main` (templates still pin `@main`).
2. Dispatch `aw-release-promote` on `main` with `release-type=patch` (first run → `v0` / `v0.0.0`).
3. Open a follow-up PR that switches the shared-train client templates from `@main` → `@v0`, then redistribute. Keep pilot / guinea-pig repos (including `elastic/oblt-aw`) on `@main` for early detection.

## Scripts and workflows

| Path | Role |
|------|------|
| `.github/workflows/aw-release-promote.yml` | Promote entrypoint (calls `e2e-all`) |
| `.github/workflows/aw-release-rollback.yml` | Rollback entrypoint |
| `.github/workflows/e2e-all.yml` | Parallel leaf E2E (promote + smoke) |
| `config/release-pointers.json` | Source of truth for SHAs / semver |
| `config/release.json` | Static release-train settings (`workflow-token-policy` / `rollback-workflow-token-policy`) |
| `scripts/aw_release_merge_pointers_pr.sh` | Approve + squash-merge the pointers PR (pinned to create-pull-request head SHA) |
| `scripts/aw_release_prepare_pointers_branch.sh` | Tip vs plan-base compare; leave uncommitted pointers on the default-branch tip for create-pull-request |
| `scripts/aw_release_promote.py` | Promote CLI |
| `scripts/aw_release_rollback.py` | Rollback CLI |
| `scripts/release_pointers.py` | Library |

### Vault token policy (pointers PR)

Promote and rollback mint distinct Vault roles from [`config/release.json`](../../config/release.json) via OIDC (`elastic/oblt-actions/github/create-token`):

| Entrypoint | Config key | Role (`catalog-info`) | `bound_claims.workflow_ref` |
|------------|------------|------------------------|-----------------------------|
| `aw-release-promote.yml` | `workflow-token-policy` | `token-policy-bd2501d7d475` | `…/aw-release-promote.yml@*` |
| `aw-release-rollback.yml` | `rollback-workflow-token-policy` | `token-policy-0052d19cd01e` | `…/aw-release-rollback.yml@*` |

## References

- Issue: [#1878](https://github.com/elastic/oblt-aw/issues/1878)
- Testing platform: [agentic-workflow-testing-platform](../architecture/agentic-workflow-testing-platform.md)
- Distribution: [distribute-client-workflow](distribute-client-workflow.md)
- Client templates: [obs-aw-client-template](../workflows/obs-aw-client-template.md)

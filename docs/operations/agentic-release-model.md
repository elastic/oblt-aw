# Agentic workflow release model

**Status:** Implementation for [#1878](https://github.com/elastic/oblt-aw/issues/1878) (parent [#1879](https://github.com/elastic/oblt-aw/issues/1879)).
**Testing contract:** [agentic-workflow-testing-platform](../architecture/agentic-workflow-testing-platform.md).

## Goal

Promote control-plane changes safely with mandatory gating E2E, keep consumer trigger churn low (major bumps only), and support quick rollback.

## Current pins (inventory)

| Surface | Location | Pointer today |
|---------|----------|---------------|
| Distributed client triggers | `.github/remote-workflow-template/**/trigger-*-aw-*.yml` | Source tree pins `@main`; distribute substitutes the install pin from `pin-class` |
| Installed client triggers (incl. control plane) | `.github/workflows/trigger-*-aw-*.yml` in each active repo | `development` → `@main`; `production` → `tags.current` (`@v0`) once `pointers.current.sha` is set **and** that tag exists on origin |
| Development pins | `pin-class: development` in `config/*/active-repositories.json` | Always `@main`. `elastic/oblt-aw` must be development (live E2E consumer) |
| E2E-only schedule entry | `.github/workflows/e2e-trigger-obs-aw-schedule.yml` | Relative `./` (control-plane only; not distributed) |
| Event orchestrators → routes | `obs-aw-event-*.yml` | Relative `./` (inherits caller pin) |
| In-repo GH-AW locks | `obs-aw-autodoc.yml`, `obs-aw-dependency-review.yml`, `obs-aw-estc-pr-buildkite-detective.yml` | Relative `./gh-aw-*.lock.yml` (inherits caller pin) |
| Upstream locks still in `ai-github-actions` | Other `obs-aw-*.yml` wrappers | `elastic/ai-github-actions/...@main` (until [#1876](https://github.com/elastic/oblt-aw/issues/1876)) |
| Release metadata | `config/release-pointers.json` | `current` / `next` / `previous` SHAs + semver |

**Why development stays on `@main`:** After promote, production consumers pin the moving major (`@v0`). Development repositories (including `elastic/oblt-aw`) keep consuming tip of `main` so live schedules, PR routes, and E2E that poll real client triggers catch control-plane regressions before the shared train promotes. Parser/CI reject any `pin-class` for `elastic/oblt-aw` other than `development`.

Initial development list (everyone else in the obs/docs active lists is production):

- `elastic/oblt-actions`
- `elastic/oblt-aw`
- `elastic/oblt-infra`
- `elastic/observability-github-secrets`
- `elastic/observability-github-settings`
- `elastic/observability-robots`
- `elastic/observability-robots-playground-public`

## Target model (hybrid)

- **Shared train (default):** one moving major tag `v0` for production `pin-class` installs while the promote train is proven. Template source stays `@main`; distribute rewrites production installs to `tags.current`.
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
| Patch / minor (compatible) | None for production — retarget `v0` after promote. Development stays on `@main`. |
| Major / breaking (incl. graduate to `v1`) | Bump templates to `@v1` (or next major), redistribute |

## Automation vs human gates

| Step | Mode |
|------|------|
| Merge to `main` | Automated CI (unit, functional, integration) |
| Promote (`aw-release-promote.yml`) | Manual `workflow_dispatch` on `main` with `release-type` (`patch` / `minor` / `major`); calls `e2e-all` then tags the gated SHA and creates a GitHub Release |
| Rollback (`aw-release-rollback.yml`) | Manual; confirm input must be `rollback` |
| Major bump / model or security-sensitive changes | Human review before promote |

## Promote contract

1. Dispatch `aw-release-promote.yml` **on the default branch** (`main`). GitHub’s “Use workflow from” picker cannot be limited in YAML; the guard job fails closed off the default branch, and `e2e-all` / `promote` also skip via `if: github.ref_name == default_branch` (same pattern on rollback).
2. Choose `release-type`: `patch`, `minor`, or `major`. First promote (empty current pointer) always creates `v0.0.0` from `config/release-pointers.json` `major`.
3. Workflow calls `e2e-all` with `checkout-ref` set to `github.sha` (tip of `main` at promote start). Harness/oracle code is pinned to that SHA; live routes on pilot repos (including `elastic/oblt-aw`) exercise **default-branch tip** via `@main` client pins (and relative `e2e-trigger-*` where used).
4. Before mutating tags, re-fetch and require the promote SHA is an **ancestor of** `origin/main` (or still the tip). If `main` advanced during E2E, promote **continues** and tags the gated SHA.
5. On success: create immutable `vX.Y.Z` (no force-push), move `vX` / `next` / `previous`, **push tags**, then **land** `config/release-pointers.json` via a Vault-authored PR (org Require-a-PR blocks direct pushes to `main`; approve as `GITHUB_TOKEN`, squash-merge as Vault), then create a **GitHub Release** for `vX.Y.Z` with auto-generated notes (range from the prior immutable semver when present). Tags go out before the pointers merge so distribute (path filter includes `config/release-pointers.json`) never writes production `uses: @vN` for a tag that is not on origin. If that immutable tag already points at the planned SHA (retry after a failed pointers merge), skip recreate and skip pushing it; still land pointers and moving tags. Before planning a later promote or rollback, origin’s `tags.current` must match `pointers.current` or the in-flight SHA of *this* run (retry). Any other mismatch is refused so a promote cannot record the wrong `previous`. Semver bumps from the **highest** pointer semver so rollback cannot rewind immutable numbering. Before opening the pointers PR, fail closed if tip’s `release-pointers.json` differs from the plan-base SHA (re-dispatch on current tip; do not overwrite a newer promote/rollback landing).

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
| Failed pointers merge | Re-run the same rollback. Do not promote until origin `vN` matches committed pointers (or that rollback’s in-flight SHA). |
| Optional blast-radius stop | Disable routes via Control Plane Dashboard ([aw-prelude](../workflows/aw-prelude.md)) |

## First promote (after this model lands)

1. Merge the release-model PR to `main` (template source still pins `@main`).
2. Dispatch `aw-release-promote` on `main` with `release-type=patch` (first run → `v0` / `v0.0.0`).
3. Merge the follow-up that classifies active repos (`pin-class`) and teaches distribute to substitute production pins. Development installs stay `@main`. Production installs stay `@main` until `pointers.current.sha` is set and `tags.current` exists on origin.
4. After the pointers file lands on `main`, distribute runs again (path filter includes `config/release-pointers.json`) and production consumers pick up `@v0` only if that tag is already published.

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

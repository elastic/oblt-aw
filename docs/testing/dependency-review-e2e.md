# E2E harness: `obs:dependency-review`

Production end-to-end harness for Actions pin-bump pull requests. Mirrors the automerge vm-images live pattern ([automerge-vm-images-e2e](automerge-vm-images-e2e.md)) but stops after dependency-review side effects — it does **not** wait for automerge approve/merge.

## What this harness covers

Live E2E only against **`elastic/oblt-aw`**:

1. Seed [`.github/workflows/e2e-dependency-review-actions-fixture.yml`](../../.github/workflows/e2e-dependency-review-actions-fixture.yml) on the default branch **only when missing** (refuse overwrite if remote content differs). The seed pin is `actions/checkout@11bd7190…` (`# v4.2.2`).
2. Open an ephemeral same-repo PR authored as **`elastic-vault-github-plugin-prod[bot]`** via OIDC [`create-token`](https://github.com/elastic/oblt-actions/tree/v1/github/create-token) using `workflow-token-policy` from [`config/e2e.json`](../../config/e2e.json) (dedicated `token-policy-6cd7ac55e207` in `elastic/catalog-info`, bound to `e2e-*.yml`). The PR bumps the fixture pin to `actions/checkout@08eba0b2…` (`# v4.3.0`). Vault authorship avoids GitHub’s [bot PR “Approve and run” gate](https://github.blog/changelog/2026-06-11-bot-created-pull-requests-can-run-workflows-if-approved/) so `pull_request` workflows (including dependency-review) start automatically.
3. Wait for `trigger-obs-aw-pull-request.yml` → dependency-review leaf job `… / dependency-review / dependency-review / conclusion` success (nested jobs are inspected on that **caller** run — not `obs-aw-event-pull-request.yml`).
4. Wait for analysis comment presence (identity title `## Dependency Update Analysis` only — not analysis body prose) and label `oblt-aw/ai/merge-ready`.
5. Close the fixture PR and delete its branch (ephemeral).

## Live case

| Case id | Expectation |
|---------|-------------|
| `actions-pin-bump-live` | Forced Actions pin bump → dependency-review job + comment + merge-ready; no automerge wait |

## Prerequisites (live)

1. **Dashboard** — on the Control Plane Dashboard for `elastic/oblt-aw`, enable `obs:dependency-review`.
2. **Token policy** — `token-policy-6cd7ac55e207` must exist in `elastic/catalog-info` (bound to `elastic/oblt-aw/.github/workflows/e2e-*.yml@*`). Shared role name lives in [`config/e2e.json`](../../config/e2e.json) (`workflow-token-policy`); E2E workflows pass it explicitly to `create-token`.
3. **Runner identity** — live runs mint Vault via `create-token` (see [e2e-dependency-review.yml](../../.github/workflows/e2e-dependency-review.yml)). The harness reads author via the REST Pulls API (`user.login`); do not use `gh pr view --json author` (GraphQL returns `app/…` since gh ≥ 2.50).

CI for fixture PRs is skipped when the `ci-gate` job in [`ci.yml`](../../.github/workflows/ci.yml) sets `skip=true` (any same-repo PR with an `e2e:*` label and a head ref under `e2e/`). Dependency-review still runs on the fixture. **Automerge is skipped** for label `e2e:dependency-review` on branches under `e2e/dependency-review/` so applying `oblt-aw/ai/merge-ready` cannot arm `obs:automerge:github-actions` against the Actions pin-bump PR (see [`obs-aw-event-pull-request.yml`](../../.github/workflows/obs-aw-event-pull-request.yml)).

## How to run

### GitHub Actions (preferred)

```bash
gh workflow run e2e-dependency-review.yml
```

To run every leaf E2E (this one plus others): `gh workflow run e2e-all.yml`.

Triggers: `workflow_dispatch` (manual) and `workflow_call` (from `e2e-all.yml`). Concurrency group `e2e-dependency-review`.

### Harness/oracle unit coverage (no live agent)

```bash
pytest tests/e2e/test_dependency_review_e2e.py -v
```

## Artifacts

Each run uploads `e2e-dependency-review-actions-pin-bump-live-<run_id>` with `outcome.json`, `oracle-report.json`, and `summary.json`.

## Related

- Config: [`config/obs/e2e-dependency-review.json`](../../config/obs/e2e-dependency-review.json)
- Harness/oracle: [`scripts/obs/e2e/`](../../scripts/obs/e2e/)
- Fixture workflow: [`.github/workflows/e2e-dependency-review-actions-fixture.yml`](../../.github/workflows/e2e-dependency-review-actions-fixture.yml)
- Routing: [dependency-review-routing](../routing/dependency-review-routing.md)
- Workflow docs: [obs-aw-dependency-review](../workflows/obs-aw-dependency-review.md)

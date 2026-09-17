# E2E harness: `obs:automerge:vm-images`

Production end-to-end harness for updatecli-shaped VM-image bumps ([#1732](https://github.com/elastic/oblt-aw/issues/1732)). Mirrors the ESTC detective live pattern ([estc-pr-buildkite-detective-e2e](estc-pr-buildkite-detective-e2e.md)) and the playground bump shape from `elastic/observability-robots-playground-public`.

## What this harness covers

Live E2E only against **`elastic/oblt-aw`**:

1. Seed `.buildkite/pipeline.e2e-automerge-vm-images.yml` on the default branch **only when missing** (refuse overwrite if remote content differs); bump IMAGE pins on an ephemeral fixture branch (playground/updatecli `platform-ingest-elastic-agent-*` shape).
2. Open an ephemeral same-repo PR authored as **`elastic-vault-github-plugin-prod[bot]`** via OIDC [`create-token`](https://github.com/elastic/oblt-actions/tree/v1/github/create-token) using this repository’s existing `workflow-token-policy` from [`config/obs/active-repositories.json`](../../config/obs/active-repositories.json) (not `GITHUB_TOKEN` / `github-actions[bot]`). Vault authorship avoids GitHub’s [bot PR “Approve and run” gate](https://github.blog/changelog/2026-06-11-bot-created-pull-requests-can-run-workflows-if-approved/) so `pull_request` workflows (including dependency-review) start automatically.
3. Wait for `trigger-obs-aw-pull-request.yml` → dependency-review → `oblt-aw/ai/merge-ready` (nested jobs are inspected on that **caller** run).
4. Wait for automerge (`obs:automerge:vm-images`) **merge leaf** job success, plus approving review → merged or auto-merge enabled (approve is not a substitute for the merge job). Automerge approves as `github-actions[bot]` (`GITHUB_TOKEN`) when the author is Vault, then merges as Vault when `workflow-token-policy` is set.

## Live case

| Case id | Expectation |
|---------|-------------|
| `vm-images-bump-live` | Forced IMAGE bump PR → dependency-review comment + merge-ready → approving review → merged or auto-merge enabled; no dependency-collection gate skip comment |

## Prerequisites (live)

1. **Dashboard** — on the Control Plane Dashboard for `elastic/oblt-aw`, enable:
   - `obs:dependency-review`
   - `obs:automerge`
   - `obs:automerge:vm-images` (currently opt-in; harness fails closed if missing)
2. **Token policy** — `elastic/oblt-aw` must remain in [`config/obs/active-repositories.json`](../../config/obs/active-repositories.json) with a non-empty `workflow-token-policy` (same policy used by agentic routes via `aw-prelude`). The E2E workflow resolves that value and passes it to `create-token` (no separate E2E TokenPolicy).
3. **Vault bypassers** — classic BP `pull_request_bypassers` includes the Vault app when CODEOWNERS would otherwise block merge (existing onboarding).
4. **Runner identity** — live runs mint Vault via `create-token` (see [e2e-automerge-vm-images.yml](../../.github/workflows/e2e-automerge-vm-images.yml)). The harness reads author via the REST Pulls API (`user.login`); do not use `gh pr view --json author` (GraphQL returns `app/…` since gh ≥ 2.50).

CI for fixture PRs is skipped when the `ci-gate` job in [`ci.yml`](../../.github/workflows/ci.yml) sets `skip=true` (any same-repo PR with an `e2e:*` label and a head ref under `e2e/`). Agentic pull-request routes are **not** skipped (unlike the ESTC fixture).

## How to run

### GitHub Actions (preferred)

```bash
gh workflow run e2e-automerge-vm-images.yml
```

To run every leaf E2E (this one plus others): `gh workflow run e2e-all.yml`.

Triggers: `workflow_dispatch` (manual) and `workflow_call` (from `e2e-all.yml`). Concurrency group `e2e-automerge-vm-images`.

### Harness/oracle unit coverage (no live agent)

```bash
pytest tests/e2e/test_automerge_vm_images_e2e.py -v
```

## Artifacts

Each run uploads `e2e-automerge-vm-images-vm-images-bump-live-<run_id>` with `outcome.json`, `oracle-report.json`, and `summary.json`.

## Related

- Config: [`config/obs/e2e-automerge-vm-images.json`](../../config/obs/e2e-automerge-vm-images.json)
- Harness/oracle: [`scripts/obs/e2e/`](../../scripts/obs/e2e/)
- Fixture pipeline: [`.buildkite/pipeline.e2e-automerge-vm-images.yml`](../../.buildkite/pipeline.e2e-automerge-vm-images.yml)
- Playground reference: `elastic/observability-robots-playground-public` (`bump-vm-images.yml`, `updatecli/updatecli-bump-vm-images.yml`)
- Routing: [automerge-routing](../routing/automerge-routing.md)

# Agent instructions (oblt-aw / control-plane)

## GOLD — pre-commit before commit / push

**Mandatory:** follow **[`.cursor/rules/ci-precommit-before-push.mdc`](.cursor/rules/ci-precommit-before-push.mdc)**. Do not commit, push, or open/update a PR until `pre-commit run --files <touched-paths>` passes locally (same gate as CI Pre-commit, including **actionlint**). Pytest alone is not enough. Install: `pre-commit install --hook-type pre-commit --hook-type pre-push`.

## Client entrypoint changes

Use **[`.github/remote-workflow-template/`](.github/remote-workflow-template/)** as the source for distributed client workflows (per org subtree, for example `obs/.github/workflows/trigger-obs-aw-<workflow-id>.yml`, `docs/.github/workflows/trigger-docs-aw-*.yml`). See [docs/workflows/obs-aw-client-template.md](docs/workflows/obs-aw-client-template.md), [docs/workflows/docs-aw-client-template.md](docs/workflows/docs-aw-client-template.md), and [CONTRIBUTING.md](CONTRIBUTING.md).

Do not reintroduce a monolithic `oblt-aw.yml` or `oblt-aw-ingress.yml`.

## Fail-closed E2E harness / oracle changes

When hardening E2E gates (or addressing fail-closed review comments), follow **[`.cursor/rules/fail-closed-e2e-gates.mdc`](.cursor/rules/fail-closed-e2e-gates.mdc)**: walk producer → outcome → oracle → tests and close every substitute signal in one change set. Do not stop after the first named fallback. Non-empty expectation maps, typo/partial keys, and test helpers that trust `outcome.expectations` are still substitute paths — reject them in the same pass.

Also keep these live-harness lessons (from automerge vm-images E2E review):

- Poll the **caller** `trigger-obs-aw-*.yml` run (`event=pull_request`); nested reusable jobs appear there. Do **not** retarget config at `workflow_call`-only orchestrators solely because nested job *ids* are declared there.
- Match **leaf** job names (e.g. `… / automerge / automerge`, `… / automerge / approve`), not broad substrings that also hit siblings (`verify`, collection checks).
- Never `OR` distinct named jobs in waiters/oracles (approve ≠ merge).
- Seed default-branch fixtures only when missing; refuse silent overwrite when remote content differs.
- Label ensure and path-gate `_as_bool` must fail closed (no crash, no “any error ⇒ create”).

Before commit/push on harness, oracle, E2E tests, or related workflows: **`pre-commit run --files <paths>` is mandatory** (includes mypy). Pytest alone does not authorize push. See also **[`.cursor/rules/ci-precommit-before-push.mdc`](.cursor/rules/ci-precommit-before-push.mdc)**.

## Control-plane workflow naming

- Shared prelude: `.github/workflows/aw-prelude.yml` (no org prefix).
- Shared dashboard audit: `.github/workflows/aw-dashboard-audit.yml` (no org prefix; always-on from org event orchestrators, not prelude-gated).
- Observability route reusables: `.github/workflows/obs-aw-<workflow-id>.yml` (declare `shared-proceed`; prelude runs in `obs-aw-event-*` orchestrators). Workflows that invoke `gh-aw-*` must call `aw-resolve-agentic-assets.yml` per agent job (`scripts/validate_aw_workflow_resolve_agentic_assets.py`).
- Docs route reusables: `.github/workflows/docs-aw-*.yml` (same `shared-proceed` contract; prelude runs in `docs-aw-event-*` orchestrators).
- Enforced by `scripts/validate_aw_workflow_prelude.py` in CI (excludes in-repo `gh-aw-*` / `*.lock.yml` primitives from registry subject discovery).
- Some Observability-owned agentic primitives live in-repo as `gh-aw-*.md` + generated `gh-aw-*.lock.yml` (pilot: `gh-aw-estc-pr-buildkite-detective`). Edit the `.md`, then `gh aw compile <workflow-id>`. Shared compile imports: `.github/workflows/gh-aw-fragments/` (fleet defaults: `gh-aw-fragments/obs-defaults.md` for model, failure reporting, trusted users).
- Other upstream lock files in `elastic/ai-github-actions` / `elastic/docs-actions` keep the `gh-aw-*` prefix until migrated.

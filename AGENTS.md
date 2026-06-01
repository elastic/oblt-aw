# Agent instructions (oblt-aw / control-plane)

## Client entrypoint changes

Use **[`.github/remote-workflow-template/`](.github/remote-workflow-template/)** as the source for distributed client workflows (for example `obs/.github/workflows/trigger-oblt-aw.yml` and `obs/.github/workflows/oblt-aw.yml`, plus `docs/.github/workflows/trigger-docs-aw.yml` and `docs/.github/workflows/docs-aw.yml`). See [docs/workflows/oblt-aw-client-template.md](docs/workflows/oblt-aw-client-template.md), [docs/workflows/docs-aw-client-template.md](docs/workflows/docs-aw-client-template.md), and [CONTRIBUTING.md](CONTRIBUTING.md).

Consumer Observability repos use **`trigger-oblt-aw.yml`** (events) → **`oblt-aw.yml`** (`workflow_dispatch`) → **`oblt-aw-ingress.yml`** (routing).

Consumer Documentation repos use **`trigger-docs-aw.yml`** (events) → **`docs-aw.yml`** (`workflow_dispatch`) → **`docs-aw-ingress.yml`** (routing).

## Control-plane workflow naming

- Shared prelude: `.github/workflows/aw-prelude.yml` (no org prefix).
- Observability reusables: `.github/workflows/oblt-aw-<workflow-id>.yml` (routed via `oblt-aw-ingress.yml`, which calls `aw-prelude` once and dispatches eligible `route-*` jobs; individual `oblt-aw-*` wrappers do not call prelude). Enforced by `scripts/validate_aw_workflow_prelude.py` in CI.
- Docs reusables: `.github/workflows/docs-aw-*.yml` (routed via `docs-aw-ingress.yml`; same ingress/prelude model as Observability).
- Upstream lock files in `elastic/ai-github-actions` / `elastic/docs-actions` keep the `gh-aw-*` prefix.

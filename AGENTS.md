# Agent instructions (oblt-aw / control-plane)

## Client entrypoint changes

Edit client triggers and entrypoints **only** under [`.github/remote-workflow-template/`](.github/remote-workflow-template/) (for example `obs/.github/workflows/trigger-oblt-aw.yml` and `oblt-aw.yml`). **Do not** hand-edit the distributed copies under [`.github/workflows/`](.github/workflows/) (`trigger-oblt-aw.yml`, `oblt-aw.yml`, docs equivalents)—those are installed by [`distribute-client-workflow.yml`](.github/workflows/distribute-client-workflow.yml). See [.cursor/rules/distribute-client-workflow-protected.mdc](.cursor/rules/distribute-client-workflow-protected.mdc).

Ingress and route reusables (`oblt-aw-ingress.yml`, `oblt-aw-*.yml`, `docs-aw-*.yml`, …) are control-plane workflows in `.github/workflows/` and are not distribution template outputs.

See [docs/workflows/oblt-aw-client-template.md](docs/workflows/oblt-aw-client-template.md), [docs/workflows/docs-aw-client-template.md](docs/workflows/docs-aw-client-template.md), and [CONTRIBUTING.md](CONTRIBUTING.md).

Consumer Observability repos use **`trigger-oblt-aw.yml`** (events) → **`oblt-aw.yml`** (`workflow_dispatch`) → **`oblt-aw-ingress.yml`** (routing).

Consumer Documentation repos use **`trigger-docs-aw.yml`** (events) → **`docs-aw.yml`** (`workflow_dispatch`) → **`docs-aw-ingress.yml`** (routing).

## Control-plane workflow naming

- Shared prelude: `.github/workflows/aw-prelude.yml` (no org prefix).
- Observability reusables: `.github/workflows/oblt-aw-<workflow-id>.yml` (routed via `oblt-aw-ingress.yml`, which calls `aw-prelude` once and dispatches eligible `route-*` jobs; individual `oblt-aw-*` wrappers do not call prelude). Enforced by `scripts/validate_aw_workflow_prelude.py` in CI. Workflows that invoke `gh-aw-*` must call `aw-resolve-apm-assets.yml` per agent job (`scripts/validate_aw_workflow_resolve_apm_assets.py`).
- Docs reusables: `.github/workflows/docs-aw-*.yml` (routed via `docs-aw-ingress.yml`; same ingress/prelude model as Observability; same `aw-resolve-apm-assets` requirement for `gh-aw-*` jobs).
- Upstream lock files in `elastic/ai-github-actions` / `elastic/docs-actions` keep the `gh-aw-*` prefix.

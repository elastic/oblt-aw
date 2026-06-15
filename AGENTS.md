# Agent instructions (oblt-aw / control-plane)

## Client entrypoint changes

Use **[`.github/remote-workflow-template/`](.github/remote-workflow-template/)** as the source for distributed client workflows (per org subtree, for example `obs/.github/workflows/trigger-oblt-aw-<workflow-id>.yml`, `docs/.github/workflows/trigger-docs-aw-*.yml`). See [docs/workflows/oblt-aw-client-template.md](docs/workflows/oblt-aw-client-template.md), [docs/workflows/docs-aw-client-template.md](docs/workflows/docs-aw-client-template.md), and [CONTRIBUTING.md](CONTRIBUTING.md).

Do not reintroduce a monolithic `oblt-aw.yml` or `oblt-aw-ingress.yml`.

## Control-plane workflow naming

- Shared prelude: `.github/workflows/aw-prelude.yml` (no org prefix).
- Observability route reusables: `.github/workflows/oblt-aw-<workflow-id>.yml` (declare `shared-proceed`; prelude runs in `oblt-aw-event-*` orchestrators). Workflows that invoke `gh-aw-*` must call `aw-resolve-apm-assets.yml` per agent job (`scripts/validate_aw_workflow_resolve_apm_assets.py`).
- Docs route reusables: `.github/workflows/docs-aw-*.yml` (same `shared-proceed` contract; prelude runs in `docs-aw-event-*` orchestrators).
- Enforced by `scripts/validate_aw_workflow_prelude.py` in CI.
- Upstream lock files in `elastic/ai-github-actions` / `elastic/docs-actions` keep the `gh-aw-*` prefix.

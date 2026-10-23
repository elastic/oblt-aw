# Workflow: `codex-preview.yml`

## At a glance

| | |
| --- | --- |
| Platform | GitHub Actions |
| Source | [`.github/workflows/codex-preview.yml`](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/codex-preview.yml) |
| Trigger | Push to `main` or pull request with changes under `docs/**`; manual dispatch |

## Purpose

Builds and publishes an Elastic Internal Docs (Codex) preview for documentation changes. The filename is intentionally fixed because a Vault OIDC binding uses the workflow reference.

## Execution flow

The `preview` job calls `elastic/docs-actions/.github/workflows/codex-preview.yml@v1` with `path-pattern: docs/**`. It runs for the listed push and pull-request path filters, or on dispatch.

## Inputs, outputs, and access

No inputs or outputs are declared. The reusable workflow receives job-level `contents: read`, `deployments: write`, `id-token: write`, and `pull-requests: write`. No repository secret is declared in this wrapper.

## Source gap

The called reusable workflow is maintained in `elastic/docs-actions`, not checked into this repository. This page describes only the checked-in caller configuration; the referenced `@v1` implementation and Vault-side binding were not independently verified here.

## Sources

- [Caller workflow](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/codex-preview.yml)
- [Codex preview cleanup caller](codex-preview-cleanup.md)

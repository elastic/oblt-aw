# Workflow: `codex-preview-cleanup.yml`

## At a glance

| | |
| --- | --- |
| Platform | GitHub Actions |
| Source | [`.github/workflows/codex-preview-cleanup.yml`](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/codex-preview-cleanup.yml) |
| Trigger | `pull_request_target` when a pull request is closed |

## Purpose

Removes Codex preview deployments after a pull request closes. The workflow comments explain why it has no `docs/**` path filter: the pull request may have created a preview and then removed documentation changes before it closes. The reusable cleanup workflow no-ops when no matching deployment exists.

## Execution flow

The `cleanup` job calls `elastic/docs-actions/.github/workflows/codex-preview-cleanup.yml@v1`. Its job permissions are `contents: none`, `deployments: write`, and `id-token: write`; workflow-level permissions are read-only.

## Inputs, outputs, and access

No inputs, outputs, or secrets are declared.

## Source gap

The cleanup implementation is maintained in `elastic/docs-actions` and is not checked into this repository. This page covers the caller only; the referenced `@v1` implementation and Vault-side binding were not independently verified here.

## Sources

- [Cleanup caller](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/codex-preview-cleanup.yml)
- [Codex preview caller](codex-preview.md)

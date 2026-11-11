# Workflow: `codex-preview-cleanup.yml`

## At a glance

| | |
| --- | --- |
| Platform | GitHub Actions |
| Source | [`.github/workflows/codex-preview-cleanup.yml`](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/codex-preview-cleanup.yml) |
| Trigger | `pull_request` with `types: [closed]` |

## Purpose

Removes Codex preview deployments after a same-repo pull request closes. The `cleanup` job is guarded with `if: github.event.pull_request.head.repo.full_name == github.repository`, so fork pull-request close events are intentionally skipped because preview deploys are not created for forks. The workflow comments explain why it has no `docs/**` path filter: the pull request may have created a preview and then removed documentation changes before it closes. The reusable cleanup workflow no-ops when no matching deployment exists.

## Execution flow

The `cleanup` job calls `elastic/docs-actions/.github/workflows/codex-preview-cleanup.yml@v1`. Its job permissions are `contents: none`, `deployments: write`, and `id-token: write`; workflow-level permissions are read-only.

## Inputs, outputs, and access

No inputs, outputs, or secrets are declared.

## Source gap

The cleanup implementation is maintained in `elastic/docs-actions` and is not checked into this repository. This page covers the caller only; the referenced `@v1` implementation and Vault-side binding were not independently verified here.

## Sources

- [Cleanup caller](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/codex-preview-cleanup.yml)
- [Codex preview caller](codex-preview.md)

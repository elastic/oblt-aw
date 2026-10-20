# Workflow: `docs-aw-event-pull-request.yml`

## At a glance

| | |
| --- | --- |
| Platform | GitHub Actions reusable workflow |
| Source | [`.github/workflows/docs-aw-event-pull-request.yml`](../../.github/workflows/docs-aw-event-pull-request.yml) |
| Trigger | `workflow_call`, invoked by the Docs pull-request client template |

## Purpose

Implements the fork-safe collection leg for the Docs PR AI menu. It collects the pull request number on the `pull_request` event; the privileged menu work runs later from the `workflow_run` route.

## Execution flow

1. `run-aw-prelude` evaluates the `docs-aw-pr-ai-menu-collect.yml` dashboard gate and loads author allow-lists.
2. `pr-ai-menu-collect` runs for `opened`, `reopened`, `synchronize`, or `ready_for_review` pull-request actions when the gate passes.
3. The called collector writes the PR number to `pr_number.txt` and uploads a `pr-number` artifact with one-day retention.

This division keeps the collection leg on the fork-safe `pull_request` event rather than using `pull_request_target`.

## Inputs, outputs, and access

No inputs or outputs are declared on this wrapper. The collector receives the shared prelude values. Its job requests `actions: write` to upload the artifact and `contents: read`; top-level workflow permissions are `contents: read`.

## Sources

- [Event orchestrator](../../.github/workflows/docs-aw-event-pull-request.yml)
- [Collector](docs-aw-pr-ai-menu-collect.md)
- [PR menu consumer](docs-aw-pr-ai-menu.md)
- [Docs client templates](docs-aw-client-template.md)
- [Shared prelude](aw-prelude.md)

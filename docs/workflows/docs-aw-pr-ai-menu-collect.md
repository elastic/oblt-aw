# Workflow: `docs-aw-pr-ai-menu-collect.yml`

## At a glance

| | |
| --- | --- |
| Platform | GitHub Actions reusable workflow |
| Source | [`.github/workflows/docs-aw-pr-ai-menu-collect.yml`](../../.github/workflows/docs-aw-pr-ai-menu-collect.yml) |
| Trigger | `workflow_call` from the Docs pull-request event orchestrator |

## Purpose

Collects a pull request number in the fork-safe `pull_request` leg so the privileged Docs PR AI menu can use it from a later `workflow_run` event. It is a small artifact handoff, not the menu implementation.

## Execution flow

The single `collect` job runs only when `shared-proceed` is the string `true`. It writes `github.event.pull_request.number` to `pr_number.txt` and uploads the file as artifact `pr-number` with one-day retention. The caller limits the event actions to `opened`, `reopened`, `synchronize`, and `ready_for_review`.

## Inputs, outputs, and access

The `workflow_call` contract requires `shared-proceed`, the allowed PR/issue author JSON and CSV values, and `shared-token-policy`. The collector itself uses only `shared-proceed`; the other values are passed through the event orchestrator contract. It has `actions: write` and `contents: read`, and no secrets.

## Sources

- [Collector workflow](../../.github/workflows/docs-aw-pr-ai-menu-collect.yml)
- [Pull-request event orchestrator](docs-aw-event-pull-request.md)
- [Workflow-run consumer](docs-aw-event-workflow-run.md)
- [PR AI menu](docs-aw-pr-ai-menu.md)

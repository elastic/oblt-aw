# Workflow: `obs-aw-event-workflow-run.yml`

## At a glance

| | |
| --- | --- |
| Platform | GitHub Actions reusable workflow |
| Source | [`.github/workflows/obs-aw-event-workflow-run.yml`](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/obs-aw-event-workflow-run.yml) |
| Trigger | `workflow_call`, invoked by the Observability workflow-run client template |

## Purpose

Routes failed GitHub Actions workflow runs associated with pull requests to the PR Actions Detective.

## Execution flow

`run-aw-prelude` evaluates the `obs-aw-pr-actions-detective.yml` dashboard gate and does not load author allow-lists. The detective job calls `obs-aw-pr-actions-detective.yml` only when the gate passes, the event is `workflow_run`, the run failed, and the event contains at least one associated pull request.

## Inputs, outputs, and access

No inputs, outputs, or secrets are declared. Workflow-level permissions are `contents: read`; the detective job receives read access to actions and contents plus OIDC, issue, pull-request, and Copilot-request permissions.

## Sources

- [Event orchestrator](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/obs-aw-event-workflow-run.yml)
- [PR Actions Detective](obs-aw-pr-actions-detective.md)
- [Workflow-run client template](obs-aw-client-template.md)
- [Shared prelude](aw-prelude.md)

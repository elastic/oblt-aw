# Workflow: `obs-aw-event-status.yml`

## At a glance

| | |
| --- | --- |
| Platform | GitHub Actions reusable workflow |
| Source | [`.github/workflows/obs-aw-event-status.yml`](../../.github/workflows/obs-aw-event-status.yml) |
| Trigger | `workflow_call` from the Observability status client template |

## Purpose

Routes failed Buildkite commit statuses to the ESTC PR Buildkite Detective after checking the Control Plane gate.

## Execution flow

`run-aw-prelude` checks `obs-aw-estc-pr-buildkite-detective.yml` and loads allowed authors. The detective job then runs only for a `status` event with state `failure` whose context contains `buildkite`, and only when the route gate is true. It calls `obs-aw-estc-pr-buildkite-detective.yml` and forwards the required `BUILDKITE_API_TOKEN` secret.

## Inputs, outputs, and access

The workflow-call contract requires `BUILDKITE_API_TOKEN`. Top-level permissions are `contents: read`; the called detector job receives `actions: read`, `contents: read`, `id-token: write`, `issues: write`, `pull-requests: write`, and `copilot-requests: write`.

## Sources

- [Event orchestrator](../../.github/workflows/obs-aw-event-status.yml)
- [ESTC PR Buildkite Detective](obs-aw-estc-pr-buildkite-detective.md)
- [Status client template](obs-aw-client-template.md)
- [Shared prelude](aw-prelude.md)

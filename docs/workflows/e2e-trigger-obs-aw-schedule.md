# Workflow: `e2e-trigger-obs-aw-schedule.yml`

## At a glance

| | |
| --- | --- |
| Platform | GitHub Actions |
| Source | [`.github/workflows/e2e-trigger-obs-aw-schedule.yml`](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/e2e-trigger-obs-aw-schedule.yml) |
| Trigger | Manual `workflow_dispatch` only |

## Purpose

Provides a control-plane-only dispatch route for testing the Observability daily schedule orchestrator without adding E2E inputs to the distributed production schedule client.

## Execution flow

The `run-obs-aw-schedule` job calls `obs-aw-event-schedule.yml` with `schedule-profile: daily`. The optional `e2e-autodoc-mode` input defaults to `true`; its dispatch value is converted from the event input string to a boolean and forwarded to the reusable workflow, which limits autodoc to the checked-in bait file.

## Inputs, outputs, and access

`e2e-autodoc-mode` is an optional boolean input. No outputs or secrets are declared. The job requests Actions read, contents write, Copilot request write, OIDC, issue write, and pull-request write permissions; workflow-level permissions are `contents: read`.

## Sources

- [E2E schedule dispatcher](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/e2e-trigger-obs-aw-schedule.yml)
- [Schedule event orchestrator](obs-aw-event-schedule.md)
- [Autodoc E2E](e2e-autodoc.md)
- [Daily schedule client template](obs-aw-client-template.md)

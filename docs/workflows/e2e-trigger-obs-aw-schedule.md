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

The `run-obs-aw-schedule` job calls `obs-aw-event-schedule.yml` with `schedule-profile: daily`. Optional boolean inputs are converted from dispatch strings and forwarded:

- `e2e-autodoc-mode` (default `true`) limits autodoc to the checked-in bait file.
- `e2e-repo-scheduled-mode` (default `false`) forces the repo-scheduled E2E bait automation.

## Inputs, outputs, and access

`e2e-autodoc-mode` and `e2e-repo-scheduled-mode` are optional boolean inputs. No outputs or secrets are declared. The job requests Actions read, contents write, Copilot request write, OIDC, issue write, and pull-request write permissions; workflow-level permissions are `contents: read`.

## Sources

- [E2E schedule dispatcher](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/e2e-trigger-obs-aw-schedule.yml)
- [Schedule event orchestrator](obs-aw-event-schedule.md)
- [Autodoc E2E](e2e-autodoc.md)
- [Repo scheduled E2E](e2e-repo-scheduled.md)
- [Daily schedule client template](obs-aw-client-template.md)

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

The `run-obs-aw-schedule` job calls `obs-aw-event-schedule.yml` with `schedule-profile: daily`. Optional boolean inputs are converted from dispatch strings and forwarded, and `e2e-invocation-id` is passed through unchanged for run correlation:

- `e2e-autodoc-mode` (default `true`) limits autodoc to the checked-in bait file.
- `e2e-repo-scheduled-mode` (default `false`) forces the repo-scheduled E2E bait automation.
- `e2e-invocation-id` (default empty string) tags correlated E2E run selection and issue bodies.

## Inputs, outputs, and access

`e2e-autodoc-mode`, `e2e-repo-scheduled-mode`, and `e2e-invocation-id` are optional inputs. No outputs are declared. The workflow forwards `secrets.BUILDKITE_LOGS_API_TOKEN` to the called orchestrator as `BUILDKITE_API_TOKEN`.

This secret mapping is optional for autodoc-only E2E bait runs, and required only when schedule-routed automations need Buildkite log access (for example `obs:repo-scheduled` with `buildkite-logs`).

The job requests Actions read, contents write, Copilot request write, OIDC, issue write, and pull-request write permissions; workflow-level permissions are `contents: read`.

## Sources

- [E2E schedule dispatcher](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/e2e-trigger-obs-aw-schedule.yml)
- [Schedule event orchestrator](obs-aw-event-schedule.md)
- [Autodoc E2E](e2e-autodoc.md)
- [Repo scheduled E2E](e2e-repo-scheduled.md)
- [Daily schedule client template](obs-aw-client-template.md)

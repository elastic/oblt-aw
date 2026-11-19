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

The optional string `e2e-invocation-id` (default empty) is forwarded unchanged for live-E2E correlation. When set, the workflow `run-name` appends `[<id>]` and downstream routes use the value for docs-patrol concurrency isolation and repo-scheduled run/issue correlation.

## Inputs, outputs, and access

`e2e-autodoc-mode` and `e2e-repo-scheduled-mode` are optional boolean inputs; `e2e-invocation-id` is an optional string input. No outputs are declared. The workflow forwards `secrets.BUILDKITE_LOGS_API_TOKEN` to the called orchestrator as `BUILDKITE_API_TOKEN`.

This secret mapping is optional for autodoc-only E2E bait runs and is needed when schedule-routed automations use Buildkite log access (for example `obs:repo-scheduled` with `buildkite-logs`).

The job requests Actions read, contents write, Copilot request write, OIDC, issue write, and pull-request write permissions; workflow-level permissions are `contents: read`.

## Sources

- [E2E schedule dispatcher](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/e2e-trigger-obs-aw-schedule.yml)
- [Schedule event orchestrator](obs-aw-event-schedule.md)
- [Autodoc E2E](e2e-autodoc.md)
- [Repo scheduled E2E](e2e-repo-scheduled.md)
- [Daily schedule client template](obs-aw-client-template.md)

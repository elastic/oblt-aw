# Workflow: `obs-aw-event-schedule.yml`

## At a glance

| | |
| --- | --- |
| Platform | GitHub Actions reusable workflow |
| Source | [`.github/workflows/obs-aw-event-schedule.yml`](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/obs-aw-event-schedule.yml) |
| Trigger | `workflow_call` from daily/frequent/weekly schedule clients or the control-plane E2E dispatcher |

## Purpose

Shares the prelude and dispatches Observability scheduled routes by profile. Clients use separate schedules because GitHub does not identify which client schedule fired in the called workflow.

## Execution flow

The optional `schedule-profile` defaults to `daily`.

- `daily` — agent suggestions, autodoc, four security category detectors, resource-accessibility detector, and repo-scheduled.
- `frequent` — automerge-deferred and repo-scheduled; loads allowed authors.
- `weekly` — repo-scheduled only.

Each route runs only when its profile and gate match. The resource detector is schedule-only; security detectors and repo-scheduled also allow `workflow_dispatch`.

The optional `e2e-autodoc-mode` defaults to `false` and is forwarded to the autodoc workflow. The optional `e2e-repo-scheduled-mode` defaults to `false` and is forwarded to repo-scheduled so live E2E can force the checked-in bait automation. The optional `e2e-invocation-id` defaults to an empty string and is forwarded to both autodoc and repo-scheduled for live E2E correlation (docs-patrol concurrency isolation plus repo-scheduled run/issue correlation).

The control-plane E2E dispatcher calls this wrapper with the daily profile and can set these E2E inputs without adding them to distributed production schedule clients.

## Inputs, outputs, and access

Inputs: `schedule-profile` (`daily`, `frequent`, or `weekly`, default `daily`), boolean `e2e-autodoc-mode` (default `false`), boolean `e2e-repo-scheduled-mode` (default `false`), and string `e2e-invocation-id` (default empty). `e2e-autodoc-mode` and `e2e-invocation-id` are forwarded to autodoc; `e2e-repo-scheduled-mode` and `e2e-invocation-id` are forwarded to repo-scheduled. Optional secret `BUILDKITE_API_TOKEN` (from consumer `BUILDKITE_LOGS_API_TOKEN`) for repo-scheduled `buildkite-logs`. Top-level permissions are `contents: read`; called jobs receive route-specific permissions, including OIDC where required.

## Sources

- [Event orchestrator](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/obs-aw-event-schedule.yml)
- [Daily schedule client template](obs-aw-client-template.md)
- [Autodoc](obs-aw-autodoc.md)
- [Security category detectors](obs-aw-security-detector.md)
- [Automerge deferred](obs-aw-automerge-deferred.md)
- [Repo scheduled](obs-aw-repo-scheduled.md)
- [E2E schedule dispatcher](e2e-trigger-obs-aw-schedule.md)
- [Shared prelude](aw-prelude.md)

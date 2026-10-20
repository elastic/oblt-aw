# Workflow: `obs-aw-event-schedule.yml`

## At a glance

| | |
| --- | --- |
| Platform | GitHub Actions reusable workflow |
| Source | [`.github/workflows/obs-aw-event-schedule.yml`](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/obs-aw-event-schedule.yml) |
| Trigger | `workflow_call` from daily/frequent schedule clients or the control-plane E2E dispatcher |

## Purpose

Shares the prelude and dispatches daily or frequent Observability scheduled routes. Clients use separate schedules because GitHub does not identify which client schedule fired in the called workflow.

## Execution flow

The optional `schedule-profile` defaults to `daily`. `daily` loads gates for agent suggestions, autodoc, four security category detectors, and the resource-accessibility detector. `frequent` loads the automerge-deferred gate and allowed authors. Each route runs only when its profile and gate match; the resource detector is schedule-only, while the security detectors also allow `workflow_dispatch`.

The optional `e2e-autodoc-mode` defaults to `false` and is forwarded to the autodoc workflow. The control-plane E2E dispatcher calls this wrapper with the daily profile and can enable bait-only autodoc mode.

## Inputs, outputs, and access

Inputs: `schedule-profile` (`daily` or `frequent`) and boolean `e2e-autodoc-mode`. No outputs or secrets are declared. Top-level permissions are `contents: read`; called jobs receive route-specific permissions, including OIDC where required.

## Sources

- [Event orchestrator](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/obs-aw-event-schedule.yml)
- [Daily schedule client template](obs-aw-client-template.md)
- [Autodoc](obs-aw-autodoc.md)
- [Security category detectors](obs-aw-security-detector.md)
- [Automerge deferred](obs-aw-automerge-deferred.md)
- [E2E schedule dispatcher](e2e-trigger-obs-aw-schedule.md)
- [Shared prelude](aw-prelude.md)

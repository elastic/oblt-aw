# Workflow: `docs-aw-event-workflow-run.yml`

## At a glance

| | |
| --- | --- |
| Platform | GitHub Actions reusable workflow |
| Source | [`.github/workflows/docs-aw-event-workflow-run.yml`](../../.github/workflows/docs-aw-event-workflow-run.yml) |
| Trigger | `workflow_call`, invoked by the Docs workflow-run client template |

## Purpose

Runs the privileged Docs PR AI menu after a successful workflow-run event, consuming the PR number artifact produced by the pull-request collection leg.

## Execution flow

`run-aw-prelude` checks the `docs-aw-pr-ai-menu.yml` dashboard gate. `pr-ai-menu` runs when that gate passes and either the event is a successful `workflow_run` or the caller uses `workflow_dispatch`; it then invokes `docs-aw-pr-ai-menu.yml` with the shared prelude data.

The wrapper does not declare a workflow-run name or branch filter; those are properties of its client caller. The successful-run condition is evaluated by this reusable workflow.

## Inputs, outputs, and access

No inputs, outputs, or secrets are declared. The route job can read checks, write issues and pull requests, request Copilot, and use OIDC. Top-level workflow permissions are `contents: read`.

## Sources

- [Event orchestrator](../../.github/workflows/docs-aw-event-workflow-run.yml)
- [PR menu](docs-aw-pr-ai-menu.md)
- [Collector](docs-aw-pr-ai-menu-collect.md)
- [Docs client templates](docs-aw-client-template.md)
- [Shared prelude](aw-prelude.md)

# Workflow: `docs-aw-event-issues.yml`

## At a glance

| | |
| --- | --- |
| Platform | GitHub Actions reusable workflow |
| Source | [`.github/workflows/docs-aw-event-issues.yml`](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/docs-aw-event-issues.yml) |
| Trigger | `workflow_call`, invoked by the Docs issues client template |

## Purpose

Shares a single prelude across Docs issue-menu and dashboard-audit routes for issue and manual-dispatch events.

## Execution flow

| Job | Condition | What it does |
| --- | --- | --- |
| `run-aw-prelude` | Every call | Evaluates the Docs issue-menu gate; author allow-list loading is disabled. |
| `dashboard-audit` | An issue is edited and has the dashboard label | Calls `aw-dashboard-audit.yml` in `checkbox-delta` mode. |
| `ai-menu` | A new issue or manual dispatch, and the issue-menu gate passes | Calls `docs-aw-ai-menu.yml` with shared prelude outputs. |

The issue-menu route receives the allowed-author lists and token policy returned by the prelude. The event caller is responsible for the external event trigger; this reusable workflow itself declares only `workflow_call`.

## Inputs, outputs, and access

No inputs or outputs are declared. Workflow-level permissions are `contents: read`; the audit route can write issue comments, while the menu route declares its own permissions.

## Sources

- [Event orchestrator](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/docs-aw-event-issues.yml)
- [Docs issue menu](docs-aw-ai-menu.md)
- [Docs client templates](docs-aw-client-template.md)
- [Dashboard audit](aw-dashboard-audit.md)
- [Shared prelude](aw-prelude.md)

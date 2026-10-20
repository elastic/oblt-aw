# Workflow: `docs-aw-event-issue-comment.yml`

## At a glance

| | |
| --- | --- |
| Platform | GitHub Actions reusable workflow |
| Source | [`.github/workflows/docs-aw-event-issue-comment.yml`](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/docs-aw-event-issue-comment.yml) |
| Trigger | `workflow_call`, invoked by the Docs issue-comment client template |

## Purpose

Routes Docs issue-comment events through one shared prelude, then dispatches issue or pull-request AI-menu behavior based on the event object. It also records dashboard audit reasons for eligible issue comments.

## Execution flow

| Job | Condition | What it does |
| --- | --- | --- |
| `run-aw-prelude` | Comment action is `edited` | Evaluates the dashboard gate for the Docs issue and PR AI menus; it does not load author allow-lists. |
| `dashboard-audit-reason` | New comment on a non-PR issue with the dashboard label and without the audit marker | Calls the dashboard audit reusable workflow in `record-reason` mode. |
| `ai-menu` | Edited comment on a non-PR issue and the Docs issue-menu gate passes | Calls `docs-aw-ai-menu.yml` with the prelude outputs. |
| `pr-ai-menu` | Edited comment on a pull request and the PR-menu gate passes | Calls `docs-aw-pr-ai-menu.yml` with the prelude outputs. |

The called route jobs require the corresponding `shared-proceed` value to be `true`. Each route receives the shared author lists and token policy from the prelude.

## Inputs, outputs, and access

No public inputs or outputs are declared. Job-level permissions are granted to each called workflow; menu routes can write comments and use Copilot requests. Workflow-level permissions are `contents: read`.

## Sources

- [Event orchestrator](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/docs-aw-event-issue-comment.yml)
- [Docs issue menu](docs-aw-ai-menu.md)
- [Docs PR menu](docs-aw-pr-ai-menu.md)
- [Docs client templates](docs-aw-client-template.md)
- [Shared prelude](aw-prelude.md)

# Workflow: `obs-aw-event-issue-comment.yml`

## At a glance

| | |
| --- | --- |
| Platform | GitHub Actions reusable workflow |
| Source | [`.github/workflows/obs-aw-event-issue-comment.yml`](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/obs-aw-event-issue-comment.yml) |
| Trigger | `workflow_call`, invoked by the Observability issue-comment client template |

## Purpose

Routes issue comments through a shared prelude to the issue fixer and mention-in-issue workflows. Dashboard audit reason comments are recorded separately.

## Execution flow

| Job | Condition | What it does |
| --- | --- | --- |
| `run-aw-prelude` | Every call | Evaluates the issue fixer and mention route gates; does not load author lists. |
| `dashboard-audit-reason` | New comment on a labeled non-PR issue without the audit marker | Calls dashboard audit in `record-reason` mode. |
| `issue-fixer` | New `/ai implement` comment on an eligible non-onboarding issue from an owner, member, or collaborator; route gate passes | Calls `obs-aw-issue-fixer.yml`. |
| `mention-in-issue` | New `/ai` comment other than `/ai implement`, from an eligible author on an eligible non-onboarding issue; route gate passes | Calls `obs-aw-mention-in-issue.yml`. |

The issue fixer and mention routes receive shared author lists and token-policy values from the prelude. The fixer excludes security and resource-accessibility detector/triage issues.

## Inputs, outputs, and access

No inputs or outputs are declared. Top-level permissions are `contents: read`; called routes declare their own write and Copilot permissions.

## Sources

- [Event orchestrator](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/obs-aw-event-issue-comment.yml)
- [Issue fixer](obs-aw-issue-fixer.md)
- [Mention in issue](obs-aw-mention-in-issue.md)
- [Observability client templates](obs-aw-client-template.md)
- [Shared prelude](aw-prelude.md)

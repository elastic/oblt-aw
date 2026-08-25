# Workflow: `aw-dashboard-audit.yml`

## Overview

Source file: [.github/workflows/aw-dashboard-audit.yml](../../.github/workflows/aw-dashboard-audit.yml)

Shared (org-agnostic) reusable workflow that audits Control Plane Dashboard checkbox enable/disable changes as **comments on the same dashboard issue**. It is not gated by [aw-prelude](aw-prelude.md) or dashboard checkboxes, so auditing still runs when workflows are disabled.

Related issue: [elastic/observability-robots#4899](https://github.com/elastic/observability-robots/issues/4899)

### Jobs (Actions UI)

| Job id | Role |
|--------|------|
| `audit-dashboard` | Diffs checkbox state and posts or updates audit comments |

## Contract

### Inputs

| Input | Type | Purpose |
|-------|------|---------|
| `mode` | string | `checkbox-delta` (issues `edited`) or `record-reason` (issue_comment `created`) |

### Behavior

| Mode | Trigger (via org event orchestrators) | Action |
|------|----------------------------------------|--------|
| `checkbox-delta` | `issues` `edited` on label `oblt-aw/dashboard` | Diff `changes.body.from` vs current body; post one audit comment per changed compound id |
| `record-reason` | `issue_comment` `created` on the dashboard issue | Attach the human reply as the deactivation reason on an awaiting audit comment |

**Activation:** audit comment with when / what / who. No `@elastic/observablt-ci` mention.

**Deactivation:** audit comment asks for a reason, records when / what / who, and `@mention`s `@elastic/observablt-ci`. Reply on the same issue to fill in the reason.

**Automation:** Bot senders are skipped on the user path. Sync-driven checkbox resets are audited from [sync-control-plane-dashboard](sync-control-plane-dashboard.md) with a fixed reason (`force-sync-defaults` or `dashboard-sync`).

### Marker

Audit comments include an HTML marker such as:

```text
<!-- aw:dashboard-audit:status=awaiting-reason entry-id=<uuid> compound-id=<org:workflow> source=user -->
```

## Wiring

| Org | Issues trigger | Issues orchestrator | Issue-comment orchestrator |
|-----|----------------|---------------------|----------------------------|
| obs | `trigger-obs-aw-issues.yml` (`edited`) | `obs-aw-event-issues.yml` → `dashboard-audit` | `obs-aw-event-issue-comment.yml` → `dashboard-audit-reason` |
| docs | `trigger-docs-aw-issues.yml` (`edited`) | `docs-aw-event-issues.yml` → `dashboard-audit` | `docs-aw-event-issue-comment.yml` → `dashboard-audit-reason` |

Script: [scripts/dashboard_audit.py](../../scripts/dashboard_audit.py)

## References

- [Control Plane Dashboard — user instructions](../operations/control-plane-dashboard.md)
- [Opt in or opt out](../guides/user/opt-in-opt-out.md)
- [sync-control-plane-dashboard](sync-control-plane-dashboard.md)
- [Routing README](../routing/README.md)

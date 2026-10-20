# Workflow: `obs-aw-event-issues.yml`

## At a glance

| | |
| --- | --- |
| Platform | GitHub Actions reusable workflow |
| Source | [`.github/workflows/obs-aw-event-issues.yml`](../../.github/workflows/obs-aw-event-issues.yml) |
| Trigger | `workflow_call`, invoked by the Observability issues client template |

## Purpose

Centralizes issue-event routing for Observability triage, duplicate detection, security issue handling, resource-accessibility handling, and dashboard audit.

## Execution flow

`run-aw-prelude` evaluates the gates for seven routes and loads the author allow-lists. Other jobs are independent after the prelude:

| Route | Event/condition | Called workflow |
| --- | --- | --- |
| Dashboard audit | Edited issue carrying the dashboard label | `aw-dashboard-audit.yml` in `checkbox-delta` mode |
| Issue triage | New issue, excluding onboarding and specialized detector/triage labels | `obs-aw-issue-triage.yml` |
| Duplicate detector | New eligible issue or manual dispatch | `obs-aw-duplicate-issue-detector.yml` |
| Security superseder | New issue labeled `oblt-aw/detector/security` | `obs-aw-security-issue-superseder.yml` |
| Security triage | Security detector label added | `obs-aw-security-triage.yml` |
| Security fixer | Fix-ready and security-triage labels are both present | `obs-aw-security-fixer.yml` |
| Resource-accessibility triage | Resource-accessibility detector label added | `obs-aw-resource-not-accessible-by-integration-triage.yml` |
| Resource-accessibility fixer | Fix-ready and matching triage labels are present | `obs-aw-resource-not-accessible-by-integration-fixer.yml` |

Each route is additionally gated by the prelude's `proceed-by-workflow` result. The event client defines the external issue actions; this reusable wrapper declares only `workflow_call`.

## Inputs, outputs, and access

No inputs or outputs are declared. Top-level permissions are `contents: read`; the called jobs request route-specific issue, pull-request, Copilot, and OIDC permissions.

## Sources

- [Event orchestrator](../../.github/workflows/obs-aw-event-issues.yml)
- [Observability client templates](obs-aw-client-template.md)
- [Shared prelude](aw-prelude.md)
- [Security category detectors](obs-aw-security-detector.md)
- [Dashboard audit](aw-dashboard-audit.md)

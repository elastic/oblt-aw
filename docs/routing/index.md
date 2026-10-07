---
navigation_title: Routing
description: Event-to-workflow routing rules for OBLT Agentic Workflows.
applies_to: {}
---

# Routing

Routing rules for event-to-workflow dispatch.

## Per-workflow routing

- [Agent suggestions](agent-suggestions-routing.md)
- [Autodoc](autodoc-routing.md)
- [Automerge](automerge-routing.md)
- [Dependency review](dependency-review-routing.md)
- [Issue fixer](issue-fixer-routing.md)
- [Resource not accessible by integration](resource-not-accessible-by-integration-routing.md)
- [Security](security-routing.md)

Client template index: [Observability client templates](../workflows/obs-aw-client-template.md).

Runtime gating for agentic workflows is still read inside the ingress (`get-enabled-workflows`) when a client workflow runs. Separately, `issues.edited` on the Control Plane Dashboard issue (`label:oblt-aw/dashboard`) triggers the shared [aw-dashboard-audit](../workflows/aw-dashboard-audit.md) path (all orgs) to record enable/disable comments on that issue.

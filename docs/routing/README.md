# Routing Documentation

## Overview

This section contains the routing rules for event-to-workflow dispatch.

## Usage

Per-workflow routing (labels, triggers, and dispatch detail):

- Agent suggestions routing: [docs/routing/agent-suggestions-routing.md](agent-suggestions-routing.md)
- Autodoc routing: [docs/routing/autodoc-routing.md](autodoc-routing.md)
- Automerge routing: [docs/routing/automerge-routing.md](automerge-routing.md)
- Dependency review routing: [docs/routing/dependency-review-routing.md](dependency-review-routing.md)
- Issue fixer routing: [docs/routing/issue-fixer-routing.md](issue-fixer-routing.md)
- Resource-not-accessible-by-integration routing: [docs/routing/resource-not-accessible-by-integration-routing.md](resource-not-accessible-by-integration-routing.md)
- Security routing: [docs/routing/security-routing.md](security-routing.md)

Full registry and client template index: [docs/workflows/obs-aw-client-template.md](../workflows/obs-aw-client-template.md).

*Note: Runtime gating for agentic workflows is still read inside the ingress (`get-enabled-workflows`) when a client workflow runs. Separately, `issues.edited` on the Control Plane Dashboard issue (`label:oblt-aw/dashboard`) triggers the shared [aw-dashboard-audit](../workflows/aw-dashboard-audit.md) path (all orgs) to record enable/disable comments on that issue.*

## References

- Client templates: [.github/remote-workflow-template/obs/.github/workflows/](../../.github/remote-workflow-template/obs/.github/workflows/)

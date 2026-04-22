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

Full registry and ingress job mapping: [docs/workflows/oblt-aw-ingress.md](../workflows/oblt-aw-ingress.md).

*Note: Dashboard opt-in/opt-out is read at runtime inside the ingress (`get-enabled-workflows`); there is no `issues.edited` routing.*

## References

- Entrypoint source: [.github/workflows/oblt-aw-ingress.yml](../../.github/workflows/oblt-aw-ingress.yml)

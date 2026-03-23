# Routing Documentation

## Overview

This section contains the routing rules for event-to-workflow dispatch.

## Usage

- Dependency review routing: `docs/routing/dependency-review-routing.md`
- Resource-not-accessible-by-integration routing: `docs/routing/resource-not-accessible-by-integration-routing.md`

*Note: Dashboard opt-in/opt-out is read at runtime inside the ingress (`get_enabled_workflows`); there is no `issues.edited` routing.*

## References

- Entrypoint source: `.github/workflows/oblt-aw-ingress.yml`

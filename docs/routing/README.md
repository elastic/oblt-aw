# Routing Documentation

## Overview

This section contains the routing rules for event-to-workflow dispatch.

## Usage

- Dependency review routing: `docs/routing/dependency-review-routing.md`
- Resource-not-accessible-by-integration routing: `docs/routing/resource-not-accessible-by-integration-routing.md`
- Dashboard config sync routing: `docs/routing/dashboard-config-sync-routing.md`

## Dashboard Config Sync Routing

**Event:** `issues` with `edited` action

**Condition:** The edited issue has label `oblt-aw/dashboard`

**Routed to:** `dashboard-config-sync` job in `.github/workflows/oblt-aw-ingress.yml`

**Behavior:** Parses the dashboard issue body for checkbox state per workflow id, writes `.github/oblt-aw-config.json` in the caller repository with `enabled_workflows` array.

## References

- Entrypoint source: `.github/workflows/oblt-aw-ingress.yml`

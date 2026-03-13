# Dashboard Config Sync Routing

## Overview

Entrypoint source: `.github/workflows/oblt-aw-ingress.yml`

Routed job: `dashboard-config-sync` (ingress job, not a separate workflow file)

## Usage

Ingress routes to dashboard-config-sync when all conditions are true:

- `github.event_name == 'issues'`
- `github.event.action == 'edited'`
- The edited issue has label `oblt-aw/dashboard`

## Behavior

1. Parse the dashboard issue body for checkbox state per workflow id (pattern: `<!-- oblt-aw:workflow-id -->`)
2. Build `enabled_workflows` array from checked checkboxes
3. Write `.github/oblt-aw-config.json` in the caller repository (e.g. via PR or direct commit)

## References

- `docs/operations/control-plane-dashboard.md` — user instructions
- `docs/operations/control-plane-dashboard-format.md` — dashboard issue format and parsing rules

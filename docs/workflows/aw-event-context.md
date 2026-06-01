# Workflow: aw-event-context

## Overview

Shared reusable workflow for **event-scoped orchestrators**. Reads the Control Plane Dashboard once, optionally loads allow lists, and emits per-route `proceed-by-workflow` flags for all routes in the event family.

Called by `oblt-aw-event-pull-request.yml`, `oblt-aw-event-issues.yml`, and `oblt-aw-event-issue-comment.yml`.

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `control-plane-workflows` | yes | — | JSON array of control-plane workflow basenames to evaluate |
| `load-allowed-authors` | no | `false` | Load PR/issue allow lists when the event supports it |

## Outputs

Same dashboard and allow-list fields as [aw-prelude.md](aw-prelude.md), plus:

| Output | Description |
|--------|-------------|
| `proceed-by-workflow` | JSON map of workflow basename → `true`/`false` proceed flags |

## References

- [oblt-aw-client-template.md](oblt-aw-client-template.md)

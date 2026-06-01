# Workflow: `oblt-aw-ingress.yml`

## Overview

Central ingress reusable for Observability agentic workflows. Called from consumer `oblt-aw.yml` via `workflow_call` with relayed event context from `trigger-oblt-aw.yml`.

1. **`aw-prelude`** — reads dashboard `enabled-workflows` / `effective-raw`, PR/issue allow lists, and token policy once per ingress run
2. **Route jobs** — Each `route-*` job carries an `if:` gate for event eligibility and dashboard enablement; only matching routes call the corresponding `oblt-aw-*` reusable with relayed event context and prelude outputs (`ingress-token-policy`, allow lists). Individual `oblt-aw-*` workflows do **not** call `aw-prelude`; route eligibility is decided entirely in ingress.

Route ids and workflow files are declared in [`config/obs/workflow-registry.json`](../../config/obs/workflow-registry.json) `ingress_routes`; CI validates that registry entries match `route-*` jobs in this workflow.

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| `trigger-source` | yes | Client trigger workflow basename |
| `ingress-event-name` | yes | Original `github.event_name` |
| `ingress-event-action` | no | Original `github.event.action` |
| `ingress-event-payload-json` | yes | `toJSON(github.event)` from the trigger |
| `caller-ref` | yes | Original `github.ref` |
| `caller-sha` | yes | Original `github.sha` |
| `caller-run-id` | yes | Original `github.run_id` |

## Secrets

| Secret | Required | Used by |
|--------|----------|---------|
| `COPILOT_GITHUB_TOKEN` | no | Routed workflows that call GH-AW locks |
| `BUILDKITE_API_TOKEN` | no | `oblt-aw-estc-pr-buildkite-detective.yml` route |

## References

- [docs/workflows/oblt-aw-client-template.md](oblt-aw-client-template.md)
- [docs/routing/README.md](../routing/README.md)

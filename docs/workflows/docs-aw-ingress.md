# Workflow: `docs-aw-ingress.yml`

## Overview

Central ingress reusable for Documentation agentic workflows. Called from consumer `docs-aw.yml` via `workflow_call` with relayed event context from `trigger-docs-aw.yml`.

1. **`aw-prelude`** — reads dashboard `enabled-workflows` / `effective-raw` and token policy once per ingress run
2. **Route jobs** — Each `route-*` job gates on event eligibility and dashboard enablement; only matching routes call the corresponding `docs-aw-*` reusable with relayed event context

Route ids and workflow files are declared in [`config/docs/workflow-registry.json`](../../config/docs/workflow-registry.json) `ingress_routes`; CI validates that registry entries match `route-*` jobs in this workflow and that each `route-*` job declares `permissions` covering the called `docs-aw-*` workflow.

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

## References

- [docs/workflows/docs-aw-client-template.md](docs-aw-client-template.md)
- [docs/routing/README.md](../routing/README.md)

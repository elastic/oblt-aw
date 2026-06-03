# Workflow: `aw-prelude.yml`

## Overview

Source file: [.github/workflows/aw-prelude.yml](../../.github/workflows/aw-prelude.yml)

Shared reusable prelude for agentic workflows (dashboard read, optional allow lists).

`oblt-aw-ingress.yml` and `docs-aw-ingress.yml` each invoke this prelude once per run. Individual `oblt-aw-*` and `docs-aw-*` wrappers do **not** call prelude; route jobs in ingress gate on `enabled-workflows` and relay event context. CI enforces this via [scripts/validate_aw_workflow_prelude.py](../../scripts/validate_aw_workflow_prelude.py).

## Contract

### Inputs

| Input | Type | Default | Purpose |
|-------|------|---------|---------|
| `load-allowed-authors` | boolean | `false` | When true, loads PR and issue bot allow lists on `pull_request` / `issues` events |
| `ingress-event-name` | string | `''` | Relayed event name from ingress (empty uses `github.event_name`) |

### Outputs

| Output | Description |
|--------|-------------|
| `proceed` | Always `true` (dashboard gating is enforced per route in ingress) |
| `effective-raw` | Raw dashboard read (`''` means all workflows enabled) |
| `enabled-workflows` | Normalized JSON array of compound ids |
| `allowed-pr-authors-json` / `allowed-pr-authors-csv` | PR allow list (empty when not loaded) |
| `allowed-issue-authors-json` / `allowed-issue-authors-csv` | Issue allow list (empty when not loaded) |

Consumer workflows that call `create-token` rely on Vault auto policy per trigger `workflow_ref` (no prelude output).

## References

- [get-enabled-workflows.md](get-enabled-workflows.md)
- [load-allowed-authors.md](load-allowed-authors.md)
- [aw-resolve-apm-assets.md](aw-resolve-apm-assets.md)
- [oblt-aw-ingress.md](oblt-aw-ingress.md)
- [docs-aw-ingress.md](docs-aw-ingress.md)

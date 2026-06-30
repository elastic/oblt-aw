# Workflow: `aw-prelude.yml`

## Overview

Source file: [.github/workflows/aw-prelude.yml](../../.github/workflows/aw-prelude.yml)

Shared reusable prelude for agentic workflows (dashboard gating and optional allow lists).

Event-scoped orchestrators (`oblt-aw-event-*`, `docs-aw-event-*`) call this workflow once per GitHub event family, then fan out to per-route `*-aw-*` workflows with `shared-proceed` and related outputs. CI enforces that route reusables declare `shared-proceed` via [scripts/validate_aw_workflow_prelude.py](../../scripts/validate_aw_workflow_prelude.py).

APM asset resolution (`apm install`, `apm.yml` merge) is **not** part of the prelude. Call [aw-resolve-agentic-assets.yml](aw-resolve-agentic-assets.md) once per `gh-aw-*` agent invocation instead.

### Jobs (Actions UI)

| Job id | Role |
|--------|------|
| `read-oblt-aw-dashboard` | Calls [get-enabled-workflows.yml](../../.github/workflows/get-enabled-workflows.yml) |
| `load-oblt-aw-bot-allow-lists` | Calls [load-allowed-authors.yml](../../.github/workflows/load-allowed-authors.yml) when `load-allowed-authors` input is true |
| `evaluate-workflow-gates` | Resolves token policy, evaluates dashboard gates, packs allow-list outputs |

Event orchestrators invoke this workflow as job `run-aw-prelude`.

## Contract

### Inputs

| Input | Type | Default | Purpose |
|-------|------|---------|---------|
| `control-plane-workflows` | string | (required) | JSON array of control-plane workflow basenames to evaluate (for example `["oblt-aw-automerge.yml","oblt-aw-dependency-review.yml"]`) |
| `load-allowed-authors` | boolean | `false` | When true, loads PR and issue bot allow lists on `pull_request` / `issues` events |

### Outputs

| Output | Description |
|--------|-------------|
| `proceed-by-workflow` | JSON map of workflow basename → `true`/`false` proceed flags |
| `effective-raw` | Raw dashboard read (`''` means no open dashboard issue) |
| `enabled-workflows` | Normalized JSON array of compound ids |
| `allowed-pr-authors-json` / `allowed-pr-authors-csv` | PR allow list (empty when not loaded) |
| `allowed-issue-authors-json` / `allowed-issue-authors-csv` | Issue allow list (empty when not loaded) |
| `token-policy` | `workflow-token-policy` from `active-repositories.json` when configured |

### Gating rule

- `effective-raw` empty → no listed routes proceed
- Otherwise each route proceeds only when its registry-resolved compound id is in `enabled-workflows`

## References

- [get-enabled-workflows.md](get-enabled-workflows.md)
- [load-allowed-authors.md](load-allowed-authors.md)
- [aw-resolve-agentic-assets.md](aw-resolve-agentic-assets.md)
- [oblt-aw-client-template.md](oblt-aw-client-template.md)
- [docs-aw-client-template.md](docs-aw-client-template.md)

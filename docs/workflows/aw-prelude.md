# Workflow: `aw-prelude.yml`

## Overview

Source file: [.github/workflows/aw-prelude.yml](../../.github/workflows/aw-prelude.yml)

Shared reusable prelude for agentic workflows (dashboard gating and optional allow lists).

Every control-plane `*-aw-*` wrapper (`oblt-aw-*`, `docs-aw-*`) invokes this prelude as its first job before running agent-specific steps. CI enforces this via [scripts/validate_aw_workflow_prelude.py](../../scripts/validate_aw_workflow_prelude.py).

## Contract

### Inputs

| Input | Type | Default | Purpose |
|-------|------|---------|---------|
| `control-plane-workflow` | string | (required) | Basename of the calling wrapper (for example `oblt-aw-automerge.yml`). Prelude resolves `org:workflow-id` from that org’s [`workflow-registry.json`](../../config/obs/workflow-registry.json) `control_plane_workflows` list. |
| `load-allowed-authors` | boolean | `false` | When true, loads PR and issue bot allow lists on `pull_request` / `issues` events |

### Outputs

| Output | Description |
|--------|-------------|
| `proceed` | `true` when dashboard gating allows the workflow |
| `effective-raw` | Raw dashboard read (`''` means all workflows enabled) |
| `enabled-workflows` | Normalized JSON array of compound ids |
| `allowed-pr-authors-json` / `allowed-pr-authors-csv` | PR allow list (empty when not loaded) |
| `allowed-issue-authors-json` / `allowed-issue-authors-csv` | Issue allow list (empty when not loaded) |

### Gating rule

Same as ingress historically used:

- `effective-raw` empty → `proceed=true`
- Otherwise `proceed=true` only when the registry-resolved compound id is in `enabled-workflows`

## References

- [get-enabled-workflows.md](get-enabled-workflows.md)
- [load-allowed-authors.md](load-allowed-authors.md)
- [oblt-aw-client-template.md](oblt-aw-client-template.md)

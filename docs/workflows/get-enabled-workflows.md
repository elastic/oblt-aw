# Workflow: `get-enabled-workflows.yml`

## Overview

Source file: [.github/workflows/get-enabled-workflows.yml](../../.github/workflows/get-enabled-workflows.yml)

This reusable workflow reads the Control Plane Dashboard issue (`oblt-aw/dashboard`) and emits normalized outputs consumed by ingress gating.

It does not route agentic workflows directly. It only resolves dashboard state into a stable contract for downstream `if:` conditions.

## Usage

Triggers:

- `workflow_call`
- `workflow_dispatch`

Called by ingress:

- [.github/workflows/oblt-aw-ingress.yml](../../.github/workflows/oblt-aw-ingress.yml), job `dashboard-enabled-workflows`

## API / Interface

`workflow_call` outputs:

| Output | Type | Meaning |
|--------|------|---------|
| `enabled-workflows` | JSON array string | Normalized array (`[]` or `["org:workflow-id", ...]`) used by ingress `contains(fromJSON(...), 'org:workflow-id')` checks |
| `effective-raw` | string | Pre-normalization signal from dashboard read: `''` (no open dashboard issue), `[]`, or `["org:workflow-id", ...]` |

Semantics used by ingress:

- `effective-raw == ''`: no open dashboard issue exists; ingress treats all registry workflows as enabled.
- `effective-raw != ''` and `enabled-workflows == []`: dashboard exists but nothing is selected; gated workflows do not run.
- `effective-raw != ''` and non-empty `enabled-workflows`: only listed compound ids (`org:workflow-id`) are enabled.

## Dashboard Parsing and Normalization

The workflow fetches the first open issue with label `oblt-aw/dashboard`, then parses checked task-list entries matching the three-part marker at line start:

`^- [x] <!-- oblt-aw:<org-key>:<workflow-id> -->`

Legacy two-part lines (`<!-- oblt-aw:<workflow-id> -->` without an org) are treated as **`obs:<workflow-id>`**.

Normalization behavior:

- Empty or missing dashboard content normalizes to `[]` for `enabled-workflows`.
- Non-array payloads are normalized into unique compound ids (bare tokens get an `obs:` prefix).
- `effective-raw` is emitted separately to preserve the "no dashboard issue" signal.

## Configuration

Top-level permissions:

- `contents: read`
- `issues: read`

The job checks out **`elastic/oblt-aw`** at `main` with **sparse checkout** (`fetch-depth: 1`): only `scripts/get_enabled_workflows.py` and `scripts/common.py` (the latter is required for `from common import ...`). This matches the pattern used in [.github/workflows/load-allowed-pr-authors.yml](../../.github/workflows/load-allowed-pr-authors.yml) for minimal clones.

## References

- [docs/workflows/oblt-aw-ingress.md](oblt-aw-ingress.md)
- [docs/operations/control-plane-dashboard.md](../operations/control-plane-dashboard.md)
- [docs/operations/control-plane-dashboard-format.md](../operations/control-plane-dashboard-format.md)

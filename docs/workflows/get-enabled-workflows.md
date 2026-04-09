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
| `enabled-workflows` | JSON array string | Normalized array (`[]` or `["id", ...]`) used by ingress `contains(fromJSON(...), '<id>')` checks |
| `effective-raw` | string | Pre-normalization signal from dashboard read: `''` (no open dashboard issue), `[]`, or `["id", ...]` |

Semantics used by ingress:

- `effective-raw == ''`: no open dashboard issue exists; ingress treats all registry workflows as enabled.
- `effective-raw != ''` and `enabled-workflows == []`: dashboard exists but nothing is selected; gated workflows do not run.
- `effective-raw != ''` and non-empty `enabled-workflows`: only listed registry IDs are enabled.

## Dashboard Parsing and Normalization

The workflow fetches the first open issue with label `oblt-aw/dashboard`, then parses checked task-list entries matching:

`^- [x] <!-- oblt-aw:workflow-id -->`

Normalization behavior:

- Empty or missing dashboard content normalizes to `[]` for `enabled-workflows`.
- Non-array payloads are normalized into unique lowercase-hyphen token arrays.
- `effective-raw` is emitted separately to preserve the "no dashboard issue" signal.

## Configuration

Top-level permissions:

- `contents: read`
- `issues: read`

## References

- [docs/workflows/oblt-aw-ingress.md](oblt-aw-ingress.md)
- [docs/operations/control-plane-dashboard.md](../operations/control-plane-dashboard.md)
- [docs/operations/control-plane-dashboard-format.md](../operations/control-plane-dashboard-format.md)

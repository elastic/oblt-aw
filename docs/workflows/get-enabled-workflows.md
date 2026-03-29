# Workflow: `get-enabled-workflows.yml`

## Overview

Source file: `.github/workflows/get-enabled-workflows.yml`

This reusable workflow reads the Control Plane Dashboard issue (`oblt-aw/dashboard`) and emits normalized outputs consumed by the ingress workflow for runtime routing gates.

## Prerequisites

- Triggered by `workflow_call` from `.github/workflows/oblt-aw-ingress.yml` (or manually via `workflow_dispatch` for troubleshooting).
- Uses `github.token` to read issues.

## Usage

The workflow has one job, `read-dashboard`, that:

- fetches the first open issue with label `oblt-aw/dashboard`
- extracts checked workflow IDs from checklist markers `- [x] <!-- oblt-aw:<id> -->`
- normalizes values to a compact JSON array string
- returns both normalized and pre-normalization outputs for downstream gating

### Normalization and gating semantics

- If no open dashboard issue exists, `effective-raw` is `''` and `enabled-workflows` is `[]`. Ingress interprets empty `effective-raw` as "no dashboard configured" and allows all gated workflows.
- If a dashboard exists and no checkboxes are selected, `effective-raw` is `[]` and `enabled-workflows` is `[]`. Ingress treats this as "configured but all disabled."
- If a dashboard exists with selections, `effective-raw` and `enabled-workflows` both represent the selected IDs as JSON arrays.

## Configuration

Top-level permissions:

- `issues: read`

## API / Interface

`workflow_call` outputs:

- `enabled-workflows`: normalized JSON array string (`[]` or `["id", ...]`)
- `effective-raw`: pre-normalization dashboard value (`''`, `[]`, or `["id", ...]`)

These are surfaced from the `read-dashboard` job outputs:

- `steps.run.outputs.enabled-workflows`
- `steps.run.outputs.effective-raw`

## References

- `docs/workflows/oblt-aw-ingress.md` (consumer and gating behavior)
- `docs/operations/control-plane-dashboard.md` (dashboard lifecycle)
- `docs/operations/control-plane-dashboard-format.md` (dashboard checkbox format)

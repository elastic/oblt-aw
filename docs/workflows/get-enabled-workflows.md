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

- [.github/workflows/aw-prelude.yml](../../.github/workflows/aw-prelude.yml), job `read-oblt-aw-dashboard`

The reusable workflow job id is `read-oblt-aw-dashboard`.

## API / Interface

`workflow_call` outputs:

| Output | Type | Meaning |
|--------|------|---------|
| `enabled-workflows` | JSON array string | Normalized array (`[]`, `["org:workflow-id", ...]`, and/or `["org:workflow-id:sub-feature-id", ...]`) used by ingress and prelude gate checks |
| `effective-raw` | string | Pre-normalization signal from dashboard read: `''` (no open dashboard issue), `[]`, or an array of compound ids |

Semantics used by ingress:

- `effective-raw == ''`: no open dashboard issue exists; gated workflows do not run.
- `effective-raw != ''` and `enabled-workflows == []`: dashboard exists but nothing is selected; gated workflows do not run.
- `effective-raw != ''` and non-empty `enabled-workflows`: only listed compound ids are enabled.
- For sub-feature ids (`org:workflow-id:sub-feature-id`), parent+sub-feature gating applies: the sub-feature entry only proceeds when both `org:workflow-id` and `org:workflow-id:sub-feature-id` are present.

## Dashboard Parsing and Normalization

The workflow fetches the first open issue with label `oblt-aw/dashboard`, then parses checked task-list entries matching markers at line start:

- Workflow marker: `^- [x] <!-- oblt-aw:<org-key>:<workflow-id> -->`
- Sub-feature marker: `^- [x] <!-- oblt-aw:<org-key>:<workflow-id>:<sub-feature-id> -->`
- Legacy marker: `^- [x] <!-- oblt-aw:<workflow-id> -->` (treated as `obs:<workflow-id>`)

Legacy two-part lines (`<!-- oblt-aw:<workflow-id> -->` without an org) are treated as **`obs:<workflow-id>`**.

Normalization behavior:

- Empty or missing dashboard content normalizes to `[]` for `enabled-workflows`.
- Non-array payloads are normalized into unique compound ids (legacy bare tokens get an `obs:` prefix).
- `effective-raw` is emitted separately to preserve the "no dashboard issue" signal.

## Configuration

Top-level permissions:

- `contents: read`
- `issues: read`

The job checks out **`elastic/oblt-aw`** at `main` with **sparse checkout** (`fetch-depth: 1`): only `scripts/get_enabled_workflows.py` and `scripts/common.py` (the latter is required for `from common import ...`). This matches the pattern used in [.github/workflows/load-allowed-authors.yml](../../.github/workflows/load-allowed-authors.yml) for minimal clones.

## References

- [docs/workflows/aw-prelude.md](aw-prelude.md)
- [docs/operations/control-plane-dashboard.md](../operations/control-plane-dashboard.md)
- [docs/operations/control-plane-dashboard-format.md](../operations/control-plane-dashboard-format.md)

# Opt in or opt out

## Overview

Workflow enablement is controlled **only** through the Control Plane Dashboard issue in your repository — not through `active-repositories.json` or config files in the consumer repo.

## Prerequisites

- Your repository has an open Control Plane Dashboard issue (`label:oblt-aw/dashboard`, title `[oblt-aw] Control Plane Dashboard`). If it does not exist, complete [Start from scratch](start-from-scratch.md) first.

## Steps

### Opt in (enable a workflow)

1. Open the Control Plane Dashboard issue in your repository.
2. Find the workflow and **check** its checkbox. GitHub saves the change immediately when you click the checkbox (no separate Save step).
3. Wait for the next client workflow run on a supported trigger. The ingress reads dashboard state at runtime via [get-enabled-workflows](../../workflows/get-enabled-workflows.md).

Full UI steps: [Control Plane Dashboard — enabling a workflow](../../operations/control-plane-dashboard.md#enabling-a-workflow).

### Opt out (disable a workflow)

1. Open the Control Plane Dashboard issue.
2. **Uncheck** the workflow’s checkbox. GitHub saves the change immediately when you click the checkbox (no separate Save step).

The workflow is excluded from `enabled-workflows` on the next client run. Full UI steps: [Control Plane Dashboard — disabling a workflow](../../operations/control-plane-dashboard.md#disabling-a-workflow).

## Default behavior

| Dashboard state | Result |
|-----------------|--------|
| No dashboard exists | All workflows are deactivated |
| Dashboard exists, all checkboxes unchecked | All workflows are deactivated |
| Dashboard exists, some checkboxes checked | Only checked workflows run |

Dashboard edits do **not** trigger workflows by themselves. There is no `issues.edited` routing — gating is read inside the ingress when a client workflow runs. See [routing README note](../../routing/README.md).

## See also

- [Control Plane Dashboard — user instructions](../../operations/control-plane-dashboard.md)
- [get-enabled-workflows](../../workflows/get-enabled-workflows.md)
- [aw-prelude](../../workflows/aw-prelude.md) — how prelude consumes dashboard outputs
- [Workflow maturity badges](../../operations/control-plane-dashboard.md#maturity-badges) — `stable`, `early-adoption`, `experimental`

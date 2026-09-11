# Change maturity level

## Overview

Maturity (`stable`, `early-adoption`, `experimental`) is assigned centrally in each org’s `workflow-registry.json`. It appears as a badge on the Control Plane Dashboard and describes adoption expectations — it does not by itself enable or disable a workflow.

## Prerequisites

- Permission to open a pull request to `elastic/oblt-aw`.
- The workflow `id` and org key (`config/<org-key>/`).

## Steps

1. **Read the criteria** — See [Workflow maturity criteria](../../operations/workflow-maturity.md) for definitions of `stable`, `early-adoption`, and `experimental`.

2. **Edit `workflow-registry.json`** — Under `config/<org-key>/workflow-registry.json`, find the workflow object and set `maturity` to the new level. Example shape (from [config/obs/workflow-registry.json](../../../config/obs/workflow-registry.json)):

   ```json
   {
     "id": "automerge",
     "name": "Automerge",
     "description": "...",
     "maturity": "early-adoption",
     "default_enabled": false,
     "docs": "docs/workflows/obs-aw-automerge.md",
     "inner_workflows": ["obs-aw-automerge.yml"]
   }
   ```

3. **Review `default_enabled` if needed** — `default_enabled` controls the initial checkbox state when a **new** workflow id is synced onto a dashboard. It does not override user-edited checkboxes during normal sync. See [Workflow maturity criteria — assignment](../../operations/workflow-maturity.md#assignment).

4. **Open a pull request and merge** — After merge to `main`, [sync-control-plane-dashboard](../../workflows/sync-control-plane-dashboard.md) updates dashboard issue bodies with the new maturity badge.

5. **Confirm on a consumer dashboard** — Open a registered repo’s Control Plane Dashboard and verify the badge updated. User checkbox choices are unchanged unless you also changed `default_enabled` and used a forced sync (see [control-plane-dashboard-format](../../operations/control-plane-dashboard-format.md) for sync semantics).

## See also

- [Workflow maturity criteria](../../operations/workflow-maturity.md)
- [Control Plane Dashboard — maturity badges](../../operations/control-plane-dashboard.md#maturity-badges)
- [Add a new agentic workflow](add-a-new-agentic-workflow.md) — registering a new workflow id
- [sync-control-plane-dashboard](../../workflows/sync-control-plane-dashboard.md)

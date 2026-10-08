---
navigation_title: Workflows skipped or not running
description: Jobs skip or agents never run because Control Plane dashboard gating or registration is incomplete.
applies_to: {}
---

# Workflows skipped or not running

## Symptom

Client or framework jobs are skipped, `shared-proceed` is false, or no agent job runs after an event that should trigger a workflow.

## Cause

Runtime gating reads the Control Plane dashboard. A missing Control Plane dashboard issue, unchecked workflow row, or incomplete registration/distribution means the prelude does not proceed.

## Fix

1. Confirm an open `[oblt-aw] Control Plane Dashboard` issue and that the agentic workflow checkbox is checked — [Enable or disable an agentic workflow](../../user-guide/enable-a-new-workflow.md).
2. If the repo is new, finish onboard and merge the client install PR — [Onboard a repository](../../user-guide/onboard-a-repository.md).
3. Walk the full checklist — [Troubleshoot an error](../troubleshoot-an-error.md) (Control Plane dashboard gating, then registration/distribution).

## See also

- [get-enabled-workflows](../../workflows/get-enabled-workflows.md)
- [aw-prelude](../../workflows/aw-prelude.md)
- [Control Plane dashboard](../../operations/control-plane-dashboard.md)

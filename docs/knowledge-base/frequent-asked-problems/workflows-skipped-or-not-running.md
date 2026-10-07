---
navigation_title: Workflows skipped or not running
description: Jobs skip or agents never run because dashboard gating or registration is incomplete.
applies_to: {}
---

# Workflows skipped or not running

## Symptom

Client or control-plane jobs are skipped, `shared-proceed` is false, or no agent job runs after an event that should trigger a workflow.

## Cause

Runtime gating reads the Control Plane Dashboard. A missing dashboard issue, unchecked workflow row, or incomplete registration/distribution means the prelude does not proceed.

## Fix

1. Confirm an open `[oblt-aw] Control Plane Dashboard` issue and that the workflow checkbox is checked — [Opt in or opt out](../../user-guide/opt-in-opt-out.md).
2. If the repo is new, finish onboard and merge the client install PR — [Onboard a repository](../../user-guide/onboard-a-repository.md).
3. Walk the full checklist — [Troubleshoot an error](../../troubleshooting/troubleshoot-an-error.md) (dashboard gating, then registration/distribution).

## See also

- [get-enabled-workflows](../../workflows/get-enabled-workflows.md)
- [aw-prelude](../../workflows/aw-prelude.md)
- [Control Plane Dashboard](../../operations/control-plane-dashboard.md)

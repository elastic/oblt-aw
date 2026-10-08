---
navigation_title: Missing client template or Control Plane dashboard
description: No distribute PR or Control Plane dashboard after a repository was registered on main.
applies_to: {}
---

# Missing client template or Control Plane dashboard

## Symptom

The repository appears in `config/<org-key>/active-repositories.json` on `main`, but there is no client-template install PR and/or no `[oblt-aw] Control Plane Dashboard` issue.

## Cause

Post-registration automation creates the distribute PR and Control Plane dashboard sync from `main`. If the repo was never listed correctly, distribution/sync did not run, or the install PR was closed without merging, the consumer stays without clients or a Control Plane dashboard.

## Fix

1. Confirm the repository is listed in `config/<org-key>/active-repositories.json` on `main`.
2. Follow [distribute-client-workflow](../../operations/distribute-client-workflow.md) and [sync-control-plane-dashboard](../../workflows/sync-control-plane-dashboard.md).
3. Re-check the onboard path — [Onboard a repository](../../user-guide/onboard-a-repository.md) (troubleshooting: no install PR or Control Plane dashboard).

## See also

- [Troubleshoot an error](../../troubleshooting/troubleshoot-an-error.md)
- [Registering resources](../../onboarding/registering-a-repository.md)

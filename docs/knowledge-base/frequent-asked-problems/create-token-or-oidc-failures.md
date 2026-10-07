---
navigation_title: create-token or OIDC failures
description: Client create-token or OIDC failures from workflow_ref mismatch, missing id-token, or inactive catalog policy.
applies_to: {}
---

# create-token or OIDC failures

## Symptom

Jobs fail on `elastic/oblt-actions/github/create-token` or OIDC exchange. Logs mention Vault role, `workflow_ref`, or missing `id-token` permission.

## Cause

Common verified causes:

- Catalog token policy `workflow_ref` does not match the client trigger glob (expected `trigger-*-aw-*.yml@*`, not only `@refs/heads/main`).
- The client entrypoint job (for example `run-obs-aw-pull-request`) is missing `id-token: write`.
- Catalog policy was not merged before registration (see [Registration before catalog TokenPolicy](registration-before-catalog-token-policy.md)).

## Fix

1. Confirm `id-token: write` on the client entrypoint — [Client template index](../../workflows/obs-aw-client-template.md).
2. Align the catalog policy `workflow_ref` with distributed triggers — [Use GitHub ephemeral tokens](../../admin-guide/use-gh-ephemeral-tokens.md).
3. Use the operator checklist — [Troubleshoot an error](../../troubleshooting/troubleshoot-an-error.md) (permissions / OIDC step).

## See also

- [Registering resources — troubleshooting](../../onboarding/registering-a-repository.md#troubleshooting)
- [Configure a GitHub secret](../../troubleshooting/configure-a-github-secret.md) — when a long-lived secret is still required

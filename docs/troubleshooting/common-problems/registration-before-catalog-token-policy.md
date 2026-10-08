---
navigation_title: Registration before catalog TokenPolicy
description: Consumer automation fails because oblt-aw registration merged before the catalog-info TokenPolicy was active.
applies_to: {}
---

# Registration before catalog TokenPolicy

## Symptom

After a repository was added to `active-repositories.json`, installed client workflows fail on `create-token`. The consumer’s catalog-info TokenPolicy PR was still open or merged after registration. (Onboarding-agent mint failures use a separate policy in `config/onboard-repository.json`, not the consumer TokenPolicy.)

## Cause

The catalog-info token policy must be **merged and active** before the `elastic/oblt-aw` registration change lands on `main`. Otherwise consumer automation can call `create-token` before the policy exists.

```mermaid
flowchart LR
  A[Merge catalog-info] --> B[Merge oblt-aw registration]
  B --> C[Client create-token works]
```

## Fix

1. Merge the catalog-info TokenPolicy PR first, then registration — [Onboard a repository](../../user-guide/onboard-a-repository.md) (merge order).
2. If registration already landed too early, follow [Registering resources — troubleshooting](../../onboarding/registering-a-repository.md#troubleshooting).
3. For policy shape and OIDC claims, see [Use GitHub ephemeral tokens](../../admin-guide/use-gh-ephemeral-tokens.md).

Expected `workflow_ref` shape (ref wildcard required):

```text
elastic/<repo>/.github/workflows/trigger-obs-aw-*.yml@*
```

## See also

- [Registering resources](../../onboarding/registering-a-repository.md)
- [Troubleshoot an error](../troubleshoot-an-error.md)

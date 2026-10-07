---
navigation_title: Registration before catalog TokenPolicy
description: Consumer automation fails because oblt-aw registration merged before the catalog-info TokenPolicy was active.
applies_to: {}
---

# Registration before catalog TokenPolicy

## Symptom

After a repository was added to `active-repositories.json`, client workflows fail on `create-token`, or cross-repo onboard PRs cannot mint tokens. The catalog-info TokenPolicy PR was still open or merged after registration.

## Cause

The catalog-info token policy must be **merged and active** before the `elastic/oblt-aw` registration change lands on `main`. Otherwise consumer automation can call `create-token` before the policy exists.

## Fix

1. Merge the catalog-info TokenPolicy PR first, then registration — [Onboard a repository](../../user-guide/onboard-a-repository.md) (merge order).
2. If registration already landed too early, follow [Registering resources — troubleshooting](../../onboarding/registering-a-repository.md#troubleshooting).
3. For policy shape and OIDC claims, see [Use GitHub ephemeral tokens](../../admin-guide/use-gh-ephemeral-tokens.md).

## See also

- [Registering resources](../../onboarding/registering-a-repository.md)
- [Troubleshoot an error](../../troubleshooting/troubleshoot-an-error.md)

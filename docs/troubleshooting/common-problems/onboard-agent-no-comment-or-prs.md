---
navigation_title: Onboard agent no comment or PRs
description: The onboard-repository agent does not comment or open PRs because of missing write access, label, or token minting.
applies_to: {}
---

# Onboard agent no comment or PRs

## Symptom

You opened an onboard issue in `elastic/oblt-aw`, but there is no agent checklist comment and no `[oblt-aw][onboard]` pull requests. Or a partial run left some concerns missing.

## Cause

GitHub only applies the form label when the issue creator has push access on `elastic/oblt-aw`. Without write access, the label never sticks and `gh-aw-onboard-repository` does not start. Cross-repo PR creation also needs the agent TokenPolicy / minted token.

If the agent comments that the issue body was filtered by integrity policy, the run used a lock still on `min-integrity: approved` (DIFC tags human onboard issues as `none:public`). That override lives in `gh-aw-onboard-repository` source; after it merges, re-apply the onboard label to retry.

## Fix

1. Confirm you have **write** (or higher) on `elastic/oblt-aw` and that the issue has label `oblt-aw/onboard/repository`.

   ```bash
   gh issue view <n> --repo elastic/oblt-aw --json labels --jq '.labels[].name'
   ```

2. Check the Actions run for `gh-aw-onboard-repository`. Token and role detail: [gh-aw-onboard-repository](../../workflows/gh-aw-onboard-repository.md).

   ```bash
   gh run list --repo elastic/oblt-aw --workflow gh-aw-onboard-repository.lock.yml --limit 5
   ```

3. **Retry after a partial run** — For Phase 1, remove and re-apply `oblt-aw/onboard/repository` (or leave Phase 1 checked and re-apply the label). For Phase 2, ensure the Phase 1 catalog-info PR is **merged**, then check **Phase 2 — Remaining PRs** on the issue. The agent does not open duplicates for concerns that already have an open `[oblt-aw][onboard]` PR; it gap-fills missing concerns for the active phase and comments with PR URLs when that phase is complete.

4. **Phase 2 was unchecked by the agent** — Phase 2 ran before the catalog-info PR merged (or before the onboard TokenPolicy selector listed the consumer). Read the abort comment, merge catalog-info, then check Phase 2 again.

   :::{image} ../../images/onboard-repository-issue-form.png
   :alt: Onboard a repository issue form that applies label oblt-aw/onboard/repository
   :screenshot:
   :::

## See also

- [Onboard a repository](../../user-guide/onboard-a-repository.md)
- [Troubleshoot an error](../troubleshoot-an-error.md)

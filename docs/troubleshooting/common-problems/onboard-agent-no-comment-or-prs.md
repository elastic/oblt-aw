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

## Fix

1. Confirm you have **write** (or higher) on `elastic/oblt-aw` and that the issue has label `oblt-aw/onboard/repository`.

   ```bash
   gh issue view <n> --repo elastic/oblt-aw --json labels --jq '.labels[].name'
   ```

2. Check the Actions run for `gh-aw-onboard-repository`. Token and role detail: [gh-aw-onboard-repository](../../workflows/gh-aw-onboard-repository.md).

   ```bash
   gh run list --repo elastic/oblt-aw --workflow gh-aw-onboard-repository.lock.yml --limit 5
   ```

3. **Retry after a partial run** — Remove and re-apply `oblt-aw/onboard/repository`. The agent does not open duplicates for concerns that already have an open `[oblt-aw][onboard]` PR; it gap-fills missing concerns and comments with PR URLs when the inventory is complete.

   :::{image} ../../images/onboard-repository-issue-form.png
   :alt: Onboard a repository issue form that applies label oblt-aw/onboard/repository
   :screenshot:
   :::

## See also

- [Onboard a repository](../../user-guide/onboard-a-repository.md)
- [Troubleshoot an error](../troubleshoot-an-error.md)

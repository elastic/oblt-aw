# Test minting ephemeral tokens in GH-AW lock workflows

## Overview

Temporary validation for [observability-robots#4374](https://github.com/elastic/observability-robots/issues/4374) before merging:

1. [elastic/ai-github-actions#1949](https://github.com/elastic/ai-github-actions/pull/1949) — lock workflows mint via `create-token`
2. [elastic/oblt-aw#1762](https://github.com/elastic/oblt-aw/pull/1762) — control-plane callers pass `mint-ephemeral-token` / `token-policy`

The test entrypoint is [`.github/workflows/trigger-obs-aw-test-mint-ephemeral.yml`](../../../.github/workflows/trigger-obs-aw-test-mint-ephemeral.yml). Keep it on a **throwaway PR**; do **not** merge it to `main`.

## Why this works without merging

- `pull_request` runs the workflow file from the PR head commit (no default-branch requirement).
- The filename `trigger-obs-aw-test-mint-ephemeral.yml` matches catalog TokenPolicy `token-policy-26fea8cad514` (`workflow_ref: elastic/oblt-aw/.github/workflows/trigger-obs-aw-*.yml@*`).
- After the register job has run once, you can also dispatch with `gh workflow run … --ref <branch>`.

Official `workflow_dispatch` UI still expects the file on the default branch; use the PR label path or `gh` with `--ref`.

## Prerequisites

- Open PR from branch `test/mint-ephemeral-lock-tokens` (or equivalent) into `main`.
- Label `oblt-aw/test-mint-ephemeral` exists on `elastic/oblt-aw`.
- Upstream lock branch `feat/mint-ephemeral-tokens-in-lock-workflows` still exists on `elastic/ai-github-actions`.

## Steps

1. **Open the test PR** — Push the branch and open a PR. Wait for job **Register workflow on PR branch** to succeed.
2. **Run the mint suite** — Either:
   - Add label `oblt-aw/test-mint-ephemeral` to the PR (runs probe + issue-triage + dependency-review), or
   - Dispatch a single path:

     ```bash
     gh workflow run trigger-obs-aw-test-mint-ephemeral.yml \
       --repo elastic/oblt-aw \
       --ref test/mint-ephemeral-lock-tokens \
       -f lock=probe \
       -f pull-request-number=<PR_NUMBER>
     ```

     Other `lock` values: `issue-triage`, `dependency-review`, `issue-fixer` (dispatch-only; can open a Draft PR).
3. **Confirm minting** — In the Actions run:
   - Probe job: `Create ephemeral GitHub token` succeeds and a PR comment appears (posted with the minted token).
   - Nested lock jobs: look for step **Create ephemeral GitHub token** in `activation` / `safe_outputs` (and related jobs).
4. **Close without merging** — Delete the branch after validation. Production callers stay on `#1762` + `#1949` merge order.

## What success looks like

| Check | Expected |
|-------|----------|
| Probe `create-token` | Green; policy `token-policy-26fea8cad514` |
| Probe comment | Present on the test PR |
| Lock `Create ephemeral GitHub token` | Green when `mint-ephemeral-token: true` |
| Agent side effects | Prefer noop / minimal; issue-fixer Draft only |

Agent activation may skip or noop when the event payload lacks a real issue — mint steps can still prove the OIDC path.

## Cleanup

- Close the test PR without merging.
- Optionally remove label `oblt-aw/test-mint-ephemeral` if no longer needed.
- Delete this guide and the test workflow file with the branch.

## See also

- [Use GitHub ephemeral tokens](use-gh-ephemeral-tokens.md)
- [ai-github-actions#1949](https://github.com/elastic/ai-github-actions/pull/1949)
- [oblt-aw#1762](https://github.com/elastic/oblt-aw/pull/1762)

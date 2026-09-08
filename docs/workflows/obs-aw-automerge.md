# Workflow: `obs-aw-automerge.yml`

## Overview

Source file: [.github/workflows/obs-aw-automerge.yml](../../.github/workflows/obs-aw-automerge.yml)

This workflow runs for a **single** pull request from `github.event.pull_request` (`pull_request` trigger only). It validates the PR with `GITHUB_TOKEN`, runs the GH-AW mention-in-pr approval step when validation passes, then runs **pascalgn/automerge-action** in the `automerge` job.

**Approve identity:** Always uses `GITHUB_TOKEN` (`github-actions[bot]`) — omit `github-token-policy` on the nested lock (defaults to empty). That is a different actor from Dependabot, Renovate, Vault, and other allowed bot authors, so it satisfies required review counts and org rulesets without Vault self-APPROVE. Automerge continues via job `needs` after `approve` (no workflow re-trigger required for the review). Consumer repos need “Allow GitHub Actions to create and approve pull requests” enabled.

**Merge identity:** When `shared-token-policy` is non-empty, merge uses an ephemeral Vault-app token so squash-merge runs as that app (classic BP `pull_request_bypassers` can skip CODEOWNERS). When empty, merge uses `GITHUB_TOKEN`. `MERGE_REQUIRED_APPROVALS` is always `1`. If the merge attempt reports `merge_failed` or `not_ready`, the workflow runs `enable-merge-when-ready` to retry a direct REST merge with the same token identity, then falls back to native GitHub auto-merge (`gh pr merge --auto --squash`). If the PR remains unmerged and auto-merge was not enabled, `report-automerge-outcome` fails the workflow and upserts a PR comment. Required status checks are **not** queried in `verify`; branch protection and merge readiness checks handle gating before merge.

Ingress selects which events dispatch here; see [Automerge routing](../routing/automerge-routing.md).

## Prerequisites

- Triggered via `workflow_call` from `trigger-obs-aw-automerge.yml` when prelude and route guards match author, `oblt-aw/ai/merge-ready`, and the right `pull_request` action.
- `github.event.pull_request` must be populated (same as dependency-review PR flows).

## Usage

Jobs:

- `verify`: shallow sparse checkout of `elastic/oblt-aw` (`allowed_pr_authors.json`, `validateAutomergePr.ts`, and npm manifests only), then runs `scripts/obs/validateAutomergePr.ts` for `github.event.pull_request.number` (author allow list aligned with dependency-review, merge-ready label, draft/fork/ref).
- `check-dependency-collection`: shallow sparse checkout of `elastic/oblt-aw` (collection config, gate scripts, and `package.json` / lockfile only), then classifies the PR by changed file paths against [config/obs/automerge-dependency-collections.json](../../config/obs/automerge-dependency-collections.json); skips `approve`/`automerge` when the collection is not enabled on the Control Plane Dashboard (`obs:automerge:<collection-id>` sub-features) and posts a PR comment explaining why (no extra labels in target repos). Prelude passes `shared-enabled-workflows` into this job.
- `approve`: invokes `elastic/ai-github-actions` `gh-aw-mention-in-pr.lock.yml` when `verify` and `check-dependency-collection` pass (Copilot must not call check-run APIs for gating; branch protection handles required checks at merge time). Omits `github-token-policy` (lock default empty) so the review is submitted as `github-actions[bot]` (`GITHUB_TOKEN`).
- `automerge`: when `shared-token-policy` is non-empty, mints an ephemeral Vault-app token (`create-token`) and runs **pascalgn/automerge-action** with that token; when empty, uses `GITHUB_TOKEN`. Runs on the **same** repository as the PR (`PULL_REQUEST` is the PR number), after `approve` succeeds. Sets `MERGE_REQUIRED_APPROVALS` to `1`. Squash-merge when `MERGE_LABELS`, that approval count, and GitHub mergeability align with branch protection / rulesets. Merging as the Vault app is required for repos that list the app in classic branch-protection `pull_request_bypassers` so CODEOWNERS can be bypassed on merge.
- `enable-merge-when-ready`: runs when `automerge` outputs `merge_failed` or `not_ready`; uses the same token choice (Vault when policy is set, else `GITHUB_TOKEN`), retries `PUT .../pulls/{n}/merge`, then falls back to `gh pr merge --auto --squash` when direct merge is rejected (for example merge queue). Does **not** retry on `skipped` (missing label or approvals).
- `report-automerge-outcome`: after automerge (and optional fallback), succeeds when the PR was merged or native auto-merge is enabled; otherwise upserts a single PR comment (marker `obs-aw-automerge:outcome-gate`) explaining the blocker and fails the workflow so a successful conclusion cannot hide an unmerged PR.

There is no discover step. Prelude supplies **`allowed-pr-authors-csv`** into the `approve` job’s `oblt-aw-mention-in-pr` call. Merge-ready label and PR author gating remain in `validateAutomergePr.ts` and workflow `if` conditions; the canonical PR author list is [allowed_pr_authors.json](https://github.com/elastic/oblt-aw/blob/main/config/obs/allowed_pr_authors.json).

## Configuration

`GITHUB_TOKEN` follows least privilege: workflow root is `contents: read` only; each job sets the minimum scopes it needs.

| Job | Permissions |
|-----|-------------|
| Workflow (default) | `contents: read` |
| `verify` | `actions: read`, `contents: read`, `pull-requests: read` (validate script reads the PR) |
| `check-dependency-collection` | `contents: read`, `pull-requests: write` (list PR files, post or remove gate comment) |
| `approve` | `actions: read`, `contents: write`, `discussions: write`, `issues: write`, `pull-requests: write` (GH-AW mention-in-pr via `GITHUB_TOKEN`; no OIDC mint) |
| `automerge` | `contents: write`, `pull-requests: write`, `id-token: write` (OIDC mint when policy set; merge via automerge action) |
| `enable-merge-when-ready` | `contents: write`, `pull-requests: write`, `id-token: write` (OIDC mint when policy set; direct merge / `gh pr merge --auto`) |
| `report-automerge-outcome` | `pull-requests: write` (upsert failure comment on the PR) |

### CODEOWNERS and ephemeral tokens

GitHub CODEOWNERS accepts **users and teams only**—not GitHub Apps. Listing `@elastic-vault-github-plugin-prod` in `CODEOWNERS` is rejected as an unknown owner.

Token use differs by job:

1. **`approve`:** Omit `github-token-policy` (lock default empty) — nested lock uses `GITHUB_TOKEN` and submits APPROVE as `github-actions[bot]` (satisfies required review counts / org rulesets; avoids Vault self-APPROVE). Repos must allow GitHub Actions to approve pull requests.
2. **`automerge` / merge fallback:** When `shared-token-policy` is non-empty, mint a Vault-app token and call the REST merge API as that app. Empty policy uses `secrets.GITHUB_TOKEN` (no CODEOWNERS bypass). `MERGE_REQUIRED_APPROVALS` is always `1` (pascalgn waits for the `github-actions` approval from the `approve` job).

**Consumer requirement (mandatory for newly registered repos):** Keep human/team entries in `CODEOWNERS` when that gate applies, set a non-empty `workflow-token-policy` / `shared-token-policy`, and **always** add the Vault app to classic branch-protection `pull_request_bypassers` in [elastic/observability-github-settings](https://github.com/elastic/observability-github-settings) as part of [repository onboarding](../onboarding/registering-a-repository.md) so a Vault-app merge can bypass CODEOWNERS. Org rulesets that require reviews are satisfied by the `GITHUB_TOKEN` approve step above. Example Terraform:

```hcl
required_pull_request_reviews {
  pull_request_bypassers = [
    data.github_app.elastic-vault-github-plugin-prod.node_id,
  ]
  require_code_owner_reviews      = true
  required_approving_review_count = 1
}
```


## API / Interface

`workflow_call` contract:

- **Allow list:** `needs.run-aw-prelude.outputs.allowed-pr-authors-csv` for `gh-aw-mention-in-pr.lock.yml` (from [load-allowed-authors.yml](../../.github/workflows/load-allowed-authors.yml) via prelude).
- **Token policy:** `shared-token-policy` from `aw-prelude` / `workflow-token-policy` is used for **merge** jobs (`create-token`) when non-empty. The `approve` job omits `github-token-policy` (lock default → `GITHUB_TOKEN`).

## References

- Routing rules: [docs/routing/automerge-routing.md](../routing/automerge-routing.md)

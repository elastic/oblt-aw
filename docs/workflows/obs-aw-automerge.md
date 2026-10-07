# Workflow: `obs-aw-automerge.yml`

## Overview

Source file: [.github/workflows/obs-aw-automerge.yml](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/obs-aw-automerge.yml)

This reusable `workflow_call` workflow handles a **single** pull request using `github.event.pull_request` from the caller (typically a client `pull_request` workflow). It validates the PR with `GITHUB_TOKEN`, runs the GH-AW mention-in-pr approval step when validation passes, then attempts squash-merge via **pascalgn/automerge-action**.

When required checks are still pending, the PR path **arms** the PR (bot-authored comment marker `<!-- obs-aw-automerge:armed sha=<40-hex> -->` bound to the approved head) and exits successfully — `not_ready` never fails the workflow. Deferred merge is **not** tied to CI duration: [obs-aw-automerge-deferred.yml](obs-aw-automerge-deferred.md) merges via Vault REST on the frequent schedule profile (`trigger-obs-aw-schedule-frequent.yml`).

**Approve identity (author-aware):** GitHub rejects self-APPROVE, so the approver must differ from the PR author.

| PR author | Approve token | Approver identity |
|-----------|---------------|-------------------|
| `github-actions[bot]` | `shared-token-policy` (required non-empty) | Vault app |
| Vault, Dependabot, Renovate, others | empty (`GITHUB_TOKEN`) | `github-actions[bot]` |

`verify` rejects `github-actions[bot]` authors when `shared-token-policy` is empty. Automerge continues via job `needs` after `approve` (no workflow re-trigger required for the review). Consumer repos need “Allow GitHub Actions to create and approve pull requests” enabled for the `GITHUB_TOKEN` approve path.

**Merge identity:** When `shared-token-policy` is non-empty, merge uses an ephemeral Vault-app token so squash-merge runs as that app (classic BP `pull_request_bypassers` can skip CODEOWNERS on **direct REST merge** only; a ruleset `merge_queue` also needs the Vault app as an Integration `bypass_actors` entry—see below). When empty, merge uses `GITHUB_TOKEN`. `MERGE_REQUIRED_APPROVALS` is always `1`.

Required status checks are **not** queried in `verify`; branch protection and the deferred merge path handle gating before merge.

Ingress selects which events dispatch here; see [Automerge routing](../routing/automerge-routing.md).

If you are choosing which dependency-update categories to enroll, start with [Automerge services](../user-guide/automerge-services.md).

## Prerequisites

- Triggered via `workflow_call` from `obs-aw-event-pull-request.yml` when prelude and route guards match author, `oblt-aw/ai/merge-ready`, and the right `pull_request` action.
- `github.event.pull_request` must be populated (same as dependency-review PR flows).

## Usage

Jobs:

- `verify`: shallow sparse checkout of `elastic/oblt-aw` (`allowed_pr_authors.json`, `validateAutomergePr.ts`, and npm manifests only), then runs `scripts/obs/validateAutomergePr.ts` for `github.event.pull_request.number` (author allow list aligned with dependency-review, merge-ready label, draft/fork/ref; requires non-empty `shared-token-policy` when the author is `github-actions[bot]`).
- `check-dependency-collection`: shallow sparse checkout of `elastic/oblt-aw` (collection config, gate scripts, and `package.json` / lockfile only), then classifies the PR by changed file paths against [config/obs/automerge-dependency-collections.json](https://github.com/elastic/oblt-aw/blob/main/config/obs/automerge-dependency-collections.json); skips `approve`/`automerge` when the collection is not enabled on the Control Plane Dashboard (`obs:automerge:<collection-id>` sub-features) and posts a PR comment explaining why (no extra labels in target repos). Prelude passes `shared-enabled-workflows` into this job.
- `approve`: invokes `elastic/ai-github-actions` `gh-aw-mention-in-pr.lock.yml` when `verify` and `check-dependency-collection` pass (Copilot must not call check-run APIs for gating; branch protection / deferred merge path handle required checks at merge time). The prompt injects `shared-allowed-pr-authors-csv` from [allowed_pr_authors.json](https://github.com/elastic/oblt-aw/blob/main/config/obs/allowed_pr_authors.json) (same file as `verify` / ingress — no hardcoded author list) plus the webhook login, and instructs normalizing GraphQL `app/<slug>` → `<slug>[bot]` before comparing. Sets `github-token-policy` to `shared-token-policy` only when the PR author is `github-actions[bot]`; otherwise omits / empty so the review is submitted as `github-actions[bot]` (`GITHUB_TOKEN`).
- `automerge`: when `shared-token-policy` is non-empty, mints an ephemeral Vault-app token (`create-token`) and runs **pascalgn/automerge-action** with that token; when empty, uses `GITHUB_TOKEN`. Short retries only (`MERGE_RETRIES: 3`); long CI is handled by the deferred merge path.
- `rest-merge`: runs when `automerge` outputs `merge_failed` or `not_ready`; one Vault REST squash-merge. Soft-succeeds with `merged=false` on pending-check errors; fails on other errors (for example CODEOWNERS without bypass).
- `arm-for-deferred-merge`: runs when `rest-merge` succeeded without merging; upserts the SHA-bound armed comment (`gh`) so the deferred merge path can finish later.
- `report-automerge-outcome`: succeeds when the PR was merged (pascalgn or `rest-merge`), when already armed, or when `mergeResult` is `not_ready` **and** arming succeeded (upserts the armed comment if needed); fails when `rest-merge` or arm hit a non-retryable error or other permanent blockers (marker `obs-aw-automerge:outcome-gate`).

## Configuration

`GITHUB_TOKEN` follows least privilege: workflow root is `contents: read` only; each job sets the minimum scopes it needs.

| Job | Permissions |
|-----|-------------|
| Workflow (default) | `contents: read` |
| `verify` | `actions: read`, `contents: read`, `pull-requests: read` (validate script reads the PR) |
| `check-dependency-collection` | `contents: read`, `pull-requests: write` (list PR files, post or remove gate comment) |
| `approve` | `actions: read`, `contents: write`, `discussions: write`, `issues: write`, `pull-requests: write`, `id-token: write` (GH-AW mention-in-pr; OIDC mint when `github-token-policy` is set for `github-actions[bot]` authors) |
| `automerge` | `contents: write`, `pull-requests: write`, `id-token: write` (OIDC mint when policy set; merge via automerge action) |
| `rest-merge` | `contents: write`, `pull-requests: write`, `id-token: write` (OIDC mint when policy set; REST squash-merge) |
| `arm-for-deferred-merge` | `contents: read`, `pull-requests: write` (helper checkout and armed comment) |
| `report-automerge-outcome` | `pull-requests: write` (upsert armed or failure comment on the PR) |

### CODEOWNERS and ephemeral tokens

GitHub CODEOWNERS accepts **users and teams only**—not GitHub Apps. Listing `@elastic-vault-github-plugin-prod` in `CODEOWNERS` is rejected as an unknown owner.

Token use differs by job:

1. **`approve`:** Author-aware — empty `github-token-policy` → `GITHUB_TOKEN` / `github-actions[bot]` for Vault, Dependabot, Renovate, and other non–`github-actions` authors; pass `shared-token-policy` when the author is `github-actions[bot]` so Vault submits the review (avoids self-APPROVE). Repos must allow GitHub Actions to approve pull requests for the `GITHUB_TOKEN` path.
2. **`automerge` / `rest-merge` / deferred merge path:** When `shared-token-policy` is non-empty, mint a Vault-app token and call the REST merge API as that app. Empty policy uses `GITHUB_TOKEN` (no CODEOWNERS bypass). `MERGE_REQUIRED_APPROVALS` is always `1` on the pascalgn step.

**Consumer requirement (mandatory for newly registered repos):** Keep human/team entries in `CODEOWNERS` when that gate applies, set a non-empty `workflow-token-policy` / `shared-token-policy`, and **always** add the Vault app to classic branch-protection `pull_request_bypassers` in [elastic/observability-github-settings](https://github.com/elastic/observability-github-settings) as part of [repository onboarding](../onboarding/registering-a-repository.md) so a Vault-app merge can bypass CODEOWNERS. When the default branch is protected by a ruleset with `merge_queue`, also add the Vault app as an Integration `bypass_actors` entry on that ruleset—classic `pull_request_bypassers` do not skip merge-queue enforcement. Org rulesets that require reviews are satisfied by the author-aware approve step above. Example Terraform (classic BP):

```hcl
required_pull_request_reviews {
  pull_request_bypassers = [
    data.github_app.elastic-vault-github-plugin-prod.node_id,
  ]
  require_code_owner_reviews      = true
  required_approving_review_count = 1
}
```

Example Terraform (ruleset with `merge_queue`):

```hcl
bypass_actors {
  actor_id    = tonumber(data.github_app.elastic-vault-github-plugin-prod.id)
  actor_type  = "Integration"
  bypass_mode = "always"
}
```


## API / Interface

`workflow_call` contract:

See sibling [obs-aw-automerge-deferred.md](obs-aw-automerge-deferred.md) for the deferred merge path.

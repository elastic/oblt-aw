# Workflow: `gh-aw-onboard-repository`

## Overview

Source: [.github/workflows/gh-aw-onboard-repository.md](../../.github/workflows/gh-aw-onboard-repository.md)
Generated lock: [.github/workflows/gh-aw-onboard-repository.lock.yml](../../.github/workflows/gh-aw-onboard-repository.lock.yml)

In-repo GitHub Agentic Workflow that onboards a consumer repository when an issue in **`elastic/oblt-aw`** carries the label **`oblt-aw/onboard/repository`**.

This workflow is **not** part of the consumer agentic catalog:

- Not listed in `config/<org-key>/workflow-registry.json`
- Not distributed via client `trigger-*` templates
- Not shown on the Control Plane Dashboard
- Not named `obs-aw-*` or `docs-aw-*`

## Prerequisites

- Issue created from [.github/ISSUE_TEMPLATE/onboard-repository.yml](../../.github/ISSUE_TEMPLATE/onboard-repository.yml) (or otherwise labeled `oblt-aw/onboard/repository`).
- Actor must have **`write`** (or `maintain` / `admin`) on `elastic/oblt-aw`. Lower roles can open issues but cannot apply the form label or pass the workflow role gate.
- Catalog TokenPolicy from [`config/onboard-repository.json`](../../config/onboard-repository.json) (`workflow-token-policy`) active for `elastic/oblt-aw/.github/workflows/gh-aw-onboard-repository.lock.yml` (see companion catalog-info PR). The workflow imports generic `gh-aw-fragments/ephemeral-github-token.md` and sets `WORKFLOW_TOKEN_POLICY_CONFIG=config/onboard-repository.json` (same pattern as E2E + `config/e2e.json`). That fragment resolves the policy and mints via `elastic/oblt-actions/github/create-token@v1` in activation/agent/safe_outputs/conclusion. `make compile-aw` runs `scripts/wire_ephemeral_token.py` so lock jobs prefer the minted token, then `GH_AW_GITHUB_TOKEN` / `GITHUB_TOKEN` as fallback.

## Usage

Triggers:

- `issues` `labeled` when the label is `oblt-aw/onboard/repository` (issue forms apply the label after create and emit this event)

There is **no** `workflow_dispatch` path: the agent requires the triggering issue for input parsing and `add-comment`. Retry by re-applying the onboard label (idempotent when open `[oblt-aw][onboard]` PRs already exist).

Behavior:

1. Parse **repository** (`elastic/<repo>`) and **org key** (`obs` / `docs`) from the issue.
2. Follow [Registering resources](../onboarding/registering-a-repository.md) ([pull request inventory](../onboarding/registering-a-repository.md#pull-request-inventory-separate-concerns), [consumer secrets discovery](../onboarding/registering-a-repository.md#consumer-secrets-discovery), [automation contract](../onboarding/registering-a-repository.md#automation-contract-gh-aw-onboard-repository), steps, appendix).
3. Before opening PRs, search for existing open PRs with title-prefix `[oblt-aw][onboard]` for that repository; if found, comment **exact PR URLs** and stop.
4. Otherwise open up to four **normal (non-draft)** PRs (separate concerns); do not merge them. Discover secrets from each org registry doc’s **Prerequisites** (consumer-facing names), falling back to **API / Interface** `Secret:` lines; then resolve shared modules in the secrets checkout.
5. Comment a checklist with exact PR links (safe-output `temporary_id` / `#aw_…` rewrite) and merge order on the issue.

User-facing steps: [Onboard a repository](../guides/user/onboard-a-repository.md).

## Configuration

Permissions (source intent; lock expands job-level scopes):

- Workflow: `id-token: write` for OIDC `create-token`; agent reads contents/issues/pull-requests; Copilot requests.
- Safe outputs create comments and pull requests with the minted Vault-app token (policy id from `config/onboard-repository.json`).

Safe outputs:

- `add-comment` (issue)
- `create-pull-request` with `draft: false`, `max: 4`, `auto-close-issue: false`, allowlisted repos above

## Related exclusions

Generic catalog routes skip onboard issues so they do not compete with this agent on `elastic/oblt-aw`:

- `obs-aw-issue-triage` and `obs-aw-duplicate-issue-detector` on `issues` `opened` when the title starts with `[onboard]` **or** the issue has label `oblt-aw/onboard/repository` (title covers the form create race before the label event).
- `obs-aw-issue-fixer` and `obs-aw-mention-in-issue` on `issue_comment` under the same title/label guards.

## References

- [Onboard a repository (user guide)](../guides/user/onboard-a-repository.md)
- [Registering resources](../onboarding/registering-a-repository.md)
- [Compiler upgrade / compile](compiler-upgrade.md) — `make compile-aw-check` regenerates the lock file

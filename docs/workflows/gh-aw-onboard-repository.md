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
- Catalog TokenPolicy from [`config/onboard-repository.json`](../../config/onboard-repository.json) (`workflow-token-policy`) active for `elastic/oblt-aw/.github/workflows/gh-aw-onboard-repository.lock.yml` (see companion catalog-info PR). The workflow imports generic `gh-aw-fragments/ephemeral-github-token.md` and sets `WORKFLOW_TOKEN_POLICY_CONFIG=config/onboard-repository.json` (same pattern as E2E + `config/e2e.json`). That fragment resolves the policy and mints via `elastic/oblt-actions/github/create-token@v1` in activation/agent/safe_outputs/conclusion. `make compile-aw` runs `scripts/wire_ephemeral_token.py` so lock jobs prefer the minted token, then `GH_AW_GITHUB_TOKEN` / `GITHUB_TOKEN` as fallback.

## Usage

Triggers:

- `issues` `opened` or `labeled` when the issue has label `oblt-aw/onboard/repository`
- `workflow_dispatch` (compiler-added manual path)

Behavior:

1. Parse **repository** (`elastic/<repo>`) and **org key** (`obs` / `docs`) from the issue.
2. Follow [Registering resources](../onboarding/registering-a-repository.md).
3. Open up to four **normal (non-draft)** PRs (separate concerns); do not merge them.
4. Comment a checklist and merge order on the issue.

User-facing steps: [Onboard a repository](../guides/user/onboard-a-repository.md).

## Configuration

Permissions (source intent; lock expands job-level scopes):

- Workflow: `id-token: write` for OIDC `create-token`; agent reads contents/issues/pull-requests; Copilot requests.
- Safe outputs create comments and pull requests with the minted Vault-app token (policy id from `config/onboard-repository.json`).

Safe outputs:

- `add-comment` (issue)
- `create-pull-request` with `draft: false`, `max: 4`, `auto-close-issue: false`, allowlisted repos above

## Related exclusions

Generic `obs-aw-issue-triage` and `obs-aw-duplicate-issue-detector` skip issues labeled `oblt-aw/onboard/repository` so catalog routes do not compete with this agent on `elastic/oblt-aw`.

## References

- [Onboard a repository (user guide)](../guides/user/onboard-a-repository.md)
- [Registering resources](../onboarding/registering-a-repository.md)
- [Compiler upgrade / compile](compiler-upgrade.md) — `make compile-aw-check` regenerates the lock file

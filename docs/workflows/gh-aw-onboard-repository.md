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
- Cross-repository write access for opening PRs in `elastic/catalog-info`, `elastic/observability-github-settings`, and (when needed) `elastic/observability-github-secrets`.
  - **Preferred (OIDC):** catalog TokenPolicy `token-policy-995e89faa204` bound to `elastic/oblt-aw/.github/workflows/gh-aw-onboard-repository.lock.yml` (hash of that workflow path). Wire `elastic/oblt-actions/github/create-token@v1` with that policy once the catalog PR is active.
  - **Current compile path:** the generated lock uses `secrets.GH_AW_GITHUB_TOKEN` for cross-repo checkout and safe-output PR creation. Without that secret (or create-token wiring), the agent comments that PR creation cannot proceed.

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

- Agent reads contents/issues/pull-requests; Copilot requests.
- Safe outputs create comments and pull requests using `GH_AW_GITHUB_TOKEN` when set.

Safe outputs:

- `add-comment` (issue)
- `create-pull-request` with `draft: false`, `max: 4`, `auto-close-issue: false`, allowlisted repos above

## Related exclusions

Generic `obs-aw-issue-triage` and `obs-aw-duplicate-issue-detector` skip issues labeled `oblt-aw/onboard/repository` so catalog routes do not compete with this agent on `elastic/oblt-aw`.

## References

- [Onboard a repository (user guide)](../guides/user/onboard-a-repository.md)
- [Registering resources](../onboarding/registering-a-repository.md)
- [Compiler upgrade / compile](compiler-upgrade.md) — `make compile-aw-check` regenerates the lock file

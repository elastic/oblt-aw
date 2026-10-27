# Workflow: `gh-aw-onboard-repository`

## Overview

Source: [.github/workflows/gh-aw-onboard-repository.md](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/gh-aw-onboard-repository.md)
Generated lock: [.github/workflows/gh-aw-onboard-repository.lock.yml](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/gh-aw-onboard-repository.lock.yml)

In-repo GitHub Agentic Workflow that onboards a consumer repository when an issue in **`elastic/oblt-aw`** carries the label **`oblt-aw/onboard/repository`**.

This workflow is **not** part of the consumer agentic catalog:

- Not listed in `config/<org-key>/workflow-registry.json`
- Not distributed via client `trigger-*` templates
- Not shown on the Control Plane dashboard
- Not named `obs-aw-*` or `docs-aw-*`

## Prerequisites

- Issue created from [.github/ISSUE_TEMPLATE/onboard-repository.yml](https://github.com/elastic/oblt-aw/blob/main/.github/ISSUE_TEMPLATE/onboard-repository.yml) (or otherwise labeled `oblt-aw/onboard/repository`).
- Actor must have **`write`** (or `maintain` / `admin`) on `elastic/oblt-aw`. Lower roles can open issues but cannot apply the form label or pass the workflow role gate.
- Catalog TokenPolicy from [`config/onboard-repository.json`](https://github.com/elastic/oblt-aw/blob/main/config/onboard-repository.json) (`workflow-token-policy`) active for `elastic/oblt-aw/.github/workflows/gh-aw-onboard-repository.lock.yml` (see companion catalog-info PR). The workflow imports generic `gh-aw-fragments/ephemeral-github-token.md` and sets `WORKFLOW_TOKEN_POLICY_CONFIG=config/onboard-repository.json` (same pattern as E2E + `config/e2e.json`). That fragment resolves the policy and mints via `elastic/oblt-actions/github/create-token@v1` in activation/agent/safe_outputs/conclusion. Source frontmatter prefers `steps.create-token.outputs.token` before secrets on checkout, tools, and safe-outputs `github-token` fields. `make compile-aw` still runs `scripts/wire_ephemeral_token.py` for remaining compiler-emitted env token bindings and `id-token: write` on minting jobs.

## Usage

Triggers:

- `issues` `labeled` when the label is `oblt-aw/onboard/repository` (issue forms apply the label after create and emit this event)

There is **no** `workflow_dispatch` path: the agent requires the triggering issue for input parsing and `add-comment`. Retry by re-applying the onboard label (gap-fills missing inventory concerns; does not duplicate open `[oblt-aw][onboard]` PRs).

Behavior:

1. Read the triggering issue via GitHub MCP and parse **repository** (`elastic/<repo>`) and **org key** (`docs` / `obs` / `security`) from the body. Source sets `tools.github.min-integrity: none` (temporary DIFC workaround so human-authored onboard issues are readable under the default `approved` floor).
2. Follow [Registering resources](../onboarding/registering-a-repository.md) ([pull request inventory](../onboarding/registering-a-repository.md#pull-request-inventory-separate-concerns), [consumer secrets discovery](../onboarding/registering-a-repository.md#consumer-secrets-discovery), [automation contract](../onboarding/registering-a-repository.md#automation-contract-gh-aw-onboard-repository), steps, appendix).
3. Before opening PRs, search for existing open PRs with title-prefix `[oblt-aw][onboard]` for that repository; map them to inventory concerns. Do not duplicate covered concerns; **gap-fill** missing ones (especially secrets after full registry-doc discovery, and catalog settings-selector / `always_include_repos` when the repo is outside `resources/github/engineering/obs/`). Stop with **exact PR URLs** only when the inventory is complete.
4. Open up to five **normal (non-draft)** PRs (separate concerns; catalog may split into consumer TokenPolicy + settings-selector gap-fill); do not merge them. Discover secrets from **every** org registry doc’s **Prerequisites** (consumer-facing names), falling back to **API / Interface** `Secret:` lines — do **not** filter by `default_enabled`; then resolve shared modules in the secrets checkout. PR bodies must be valid Markdown (real newlines).
5. Comment with required content (parsed inputs, PR checklist, merge order, user-guide pointer) in **valid Markdown** — real newlines; full PR URLs or `#aw_…` rewrite. Heading wording is not fixed.

User-facing steps: [Onboard a repository](../user-guide/onboard-a-repository.md).

## Configuration

Permissions (source intent; lock expands job-level scopes):

- Workflow: `id-token: write` for OIDC `create-token`; agent reads contents/issues/pull-requests; Copilot requests.
- Safe outputs create comments and pull requests with the minted Vault-app token (policy id from `config/onboard-repository.json`).

Safe outputs:

- `add-comment` (issue)
- `create-pull-request` with `draft: false`, `max: 5`, `auto-close-issue: false`, allowlisted repos above

## Related exclusions

Generic catalog routes skip onboard issues so they do not compete with this agent on `elastic/oblt-aw`:

- `obs-aw-issue-triage` and `obs-aw-duplicate-issue-detector` on `issues` `opened` when the title starts with `[onboard]` **or** the issue has label `oblt-aw/onboard/repository` (title covers the form create race before the label event).
- `obs-aw-issue-fixer` and `obs-aw-mention-in-issue` on `issue_comment` under the same title/label guards.

## References

- [Onboard a repository (user guide)](../user-guide/onboard-a-repository.md)
- [Registering resources](../onboarding/registering-a-repository.md)
- [Compiler upgrade / compile](compiler-upgrade.md) — `make compile-aw-check` regenerates the lock file

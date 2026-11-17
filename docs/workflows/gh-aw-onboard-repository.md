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

- `issues` `labeled` when the label is `oblt-aw/onboard/repository` (issue forms apply the label after create and emit this event) — **Phase 1**
- `issues` `edited` when the issue still has that label (for example the human checks **Phase 2**) — **Phase 2** or no-op when nothing to do

There is **no** `workflow_dispatch` path: the agent requires the triggering issue for input parsing and `add-comment`.

### Two phases

| Phase | How it starts | What the agent opens |
|-------|---------------|----------------------|
| **1 — Catalog** | Phase 1 checkbox is checked on submit; label applied | `elastic/catalog-info` only (consumer TokenPolicy, step **2e** allowlists, **onboard agent TokenPolicy selector**) |
| **2 — Remaining PRs** | Human checks Phase 2 after catalog merges | Registration, settings, secrets (when needed), consumer `CODEOWNERS`, Renovate ignore (when enabled) |

If Phase 2 is checked while the Phase 1 catalog PR is not merged (or the onboard TokenPolicy selector still omits the consumer), the agent **aborts**: `update-issue` unchecks Phase 2 and `add-comment` explains why.

Behavior:

1. Read the triggering issue via GitHub MCP and parse **repository** (`elastic/<repo>`), **org key** (`docs` / `obs` / `security`), and phase checkboxes. Source sets `tools.github.min-integrity: none` (temporary DIFC workaround so human-authored onboard issues are readable under the default `approved` floor).
2. Follow [Registering resources](../onboarding/registering-a-repository.md) ([pull request inventory](../onboarding/registering-a-repository.md#pull-request-inventory-separate-concerns), [consumer secrets discovery](../onboarding/registering-a-repository.md#consumer-secrets-discovery), [automation contract](../onboarding/registering-a-repository.md#automation-contract-gh-aw-onboard-repository), steps including **2e** and onboard TokenPolicy selector, appendix).
3. Before opening PRs, search for existing open PRs with title-prefix `[oblt-aw][onboard]` for that repository; map them to inventory concerns. Do not duplicate covered concerns; **gap-fill** missing ones for the **active phase only**.
4. Open up to seven **normal (non-draft)** PRs across both phases (phase-scoped; catalog may split into consumer TokenPolicy + allowlist gap-fill). Do not merge them. Host steps parse the issue and, for Phase 2, check out `elastic/<repo>` into `repos/consumer` (`continue-on-error` so an early Phase 2 can still abort cleanly).
5. Comment with required content (parsed inputs, phase, PR checklist, next step) in **valid Markdown** — real newlines; full PR URLs or `#aw_…` rewrite. Heading wording is not fixed.

User-facing steps: [Onboard a repository](../user-guide/onboard-a-repository.md).

## Configuration

Permissions (source intent; lock expands job-level scopes):

- Workflow: `id-token: write` for OIDC `create-token`; agent reads contents/issues/pull-requests; Copilot requests.
- Safe outputs create comments, optional issue body updates (Phase 2 abort), and pull requests with the minted Vault-app token (policy id from `config/onboard-repository.json`).
- GitHub tools and `create-pull-request` allow `elastic/*` so Phase 2 can target the consumer repository.

Safe outputs:

- `add-comment` (issue)
- `update-issue` (body replace; Phase 2 abort uncheck only)
- `create-pull-request` with `draft: false`, `max: 7`, `auto-close-issue: false`, `allowed-repos: elastic/*`

Concurrency uses `cancel-in-progress: false` so an abort `update-issue` (which emits `edited`) does not cancel the abort run.

`make compile-aw` runs `scripts/patch_aw_onboard_edited_label.py` so job `if:` conditions require label `oblt-aw/onboard/repository` on `edited` (gh-aw’s `names` filter is labeled-only). A host step fails closed as defense in depth.

## Related exclusions

Generic catalog routes skip onboard issues so they do not compete with this agent on `elastic/oblt-aw`:

- `obs-aw-issue-triage` and `obs-aw-duplicate-issue-detector` on `issues` `opened` when the title starts with `[onboard]` **or** the issue has label `oblt-aw/onboard/repository` (title covers the form create race before the label event).
- `obs-aw-issue-fixer` and `obs-aw-mention-in-issue` on `issue_comment` under the same title/label guards.

## References

- [Onboard a repository (user guide)](../user-guide/onboard-a-repository.md)
- [Registering resources](../onboarding/registering-a-repository.md)
- [Compiler upgrade / compile](compiler-upgrade.md) — `make compile-aw-check` regenerates the lock file

---
inlined-imports: true
name: "Onboard Repository"
description: "Read an onboard-repository issue and open the required registration PRs"
imports:
  - gh-aw-fragments/elastic-tools.md
  - gh-aw-fragments/ephemeral-github-token.md
  - gh-aw-fragments/formatting.md
  - gh-aw-fragments/messages-footer.md
  - gh-aw-fragments/obs-defaults.md
  - gh-aw-fragments/rigor.md
  - gh-aw-fragments/runtime-setup.md
engine:
  id: copilot
on:
  stale-check: false
  issues:
    types: [opened, labeled]
    names: [oblt-aw/onboard/repository]
  workflow_dispatch:
  roles: [admin, maintainer, write]
  bots:
    - "github-actions[bot]"
concurrency:
  group: ${{ github.workflow }}-onboard-repository-${{ github.event.issue.number || github.run_id }}
  cancel-in-progress: true
# Policy id lives in config/onboard-repository.json (same pattern as config/e2e.json).
# Resolved by gh-aw-fragments/ephemeral-github-token.md before create-token.
env:
  WORKFLOW_TOKEN_POLICY_CONFIG: config/onboard-repository.json
permissions:
  copilot-requests: write
  actions: read
  contents: read
  issues: read
  pull-requests: read
  id-token: write
checkout:
  - fetch-depth: 0
  - repository: elastic/catalog-info
    path: repos/catalog-info
    github-token: ${{ secrets.GH_AW_GITHUB_TOKEN || secrets.GITHUB_TOKEN }}
  - repository: elastic/observability-github-settings
    path: repos/observability-github-settings
    github-token: ${{ secrets.GH_AW_GITHUB_TOKEN || secrets.GITHUB_TOKEN }}
  - repository: elastic/observability-github-secrets
    path: repos/observability-github-secrets
    github-token: ${{ secrets.GH_AW_GITHUB_TOKEN || secrets.GITHUB_TOKEN }}
tools:
  github:
    toolsets: [repos, issues, pull_requests, search, actions]
    allowed-repos:
      - "elastic/oblt-aw"
      - "elastic/catalog-info"
      - "elastic/observability-github-settings"
      - "elastic/observability-github-secrets"
      - "elastic/*"
  bash: true
  web-fetch:
network:
  allowed:
    - "docs.elastic.dev"
safe-outputs:
  activation-comments: false
  report-failed-jobs: false
  # Compile-time secrets chain; scripts/wire_ephemeral_token.py prefers create-token output.
  github-token: ${{ secrets.GH_AW_GITHUB_TOKEN || secrets.GITHUB_TOKEN }}
  add-comment:
    max: 2
    issues: true
    pull-requests: false
    discussions: false
    target: "triggering"
  create-pull-request:
    draft: false
    max: 4
    auto-close-issue: false
    title-prefix: "[oblt-aw][onboard] "
    allowed-repos:
      - "elastic/oblt-aw"
      - "elastic/catalog-info"
      - "elastic/observability-github-settings"
      - "elastic/observability-github-secrets"
strict: false
timeout-minutes: 90
---

# Onboard a consumer repository

You run **only** in `elastic/oblt-aw` when an issue is labeled `oblt-aw/onboard/repository`.
You are **not** a consumer catalog workflow: do not touch `workflow-registry.json`, client templates, or Control Plane Dashboard checkbox definitions.

## Inputs (from the issue)

Parse the issue body (sanitized context) and extract exactly:

1. **Repository** — must match `elastic/<repo>` (slug under the `elastic` org).
2. **Organization key** — must be an existing directory under `config/` in this repository (today: `obs` or `docs`).

If either value is missing, invalid, or the repository is already listed in `config/<org-key>/active-repositories.json`, call `add-comment` with a clear explanation and stop (use `noop` if no further action is possible).

## Authoritative procedure

Follow `docs/onboarding/registering-a-repository.md` for file shapes, TokenPolicy template, Vault bypassers HCL, and merge ordering.

Also read:

- `config/<org-key>/active-repositories.json` (current fleet entries)
- Client template triggers under `.github/remote-workflow-template/<org-key>/` to determine which `workflow_ref` values the TokenPolicy must cover
- Existing TokenPolicy examples under `repos/catalog-info` (paths used by that repository)
- Existing `branch-protections/<repo>/` modules under `repos/observability-github-settings` when present

## Required pull requests (normal, not draft)

Open **separate** pull requests (one concern each) with `create-pull-request`. Policy is `draft: false`. Do **not** merge any PR. `auto-close-issue` is already false — do not close the onboard issue.

| Order | `repo` | Workspace path | Change |
|------:|--------|----------------|--------|
| 1 | `elastic/catalog-info` | `repos/catalog-info` | TokenPolicy Resource(s) for the consumer’s client `workflow_ref` values (`refs/heads/main` only). Derive `token-policy-<12-char sha256(workflow ref base)>` per registering-a-repository.md. |
| 2 | `elastic/oblt-aw` | repository root | Add `{ "repository": "elastic/<repo>", "workflow-token-policy": "<catalog metadata.name>", "ai-assets-token-policy": "" }` to `config/<org-key>/active-repositories.json`. Keep JSON sorted/consistent with existing style. |
| 3 | `elastic/observability-github-settings` | `repos/observability-github-settings` | Add [elastic-vault-github-plugin-prod](https://github.com/apps/elastic-vault-github-plugin-prod) to classic BP `pull_request_bypassers` for the default branch (`branch-protections/<repo>/`). **Add** to existing lists; do not remove other bypassers. |
| 4 | `elastic/observability-github-secrets` | `repos/observability-github-secrets` | Only if registering-a-repository / per-workflow docs require secrets for this org’s intended defaults; otherwise skip and state “none” in the issue comment. |

Checkout directories must contain the file edits for each cross-repo PR. For the `elastic/oblt-aw` PR, edit files in this workflow repository checkout (workspace root).

## Issue comment (mandatory)

Before finishing, `add-comment` on the triggering issue with:

1. Parsed repository and org-key.
2. Checklist of expected PRs with links (or “skipped: none needed” for secrets).
3. **Merge order:** merge catalog-info **before** the `elastic/oblt-aw` registration PR.
4. Reminder that merges are **manual**.
5. After registration merges: expect distribute-client-workflow install PR and Control Plane Dashboard in `elastic/<repo>`; user then enables workflows on the dashboard (`docs/guides/user/onboard-a-repository.md`).

## Stop conditions

- Missing/invalid inputs → comment and stop.
- Repository already registered for that org-key → comment and stop (do not open duplicate registration PRs).
- Insufficient permissions / missing cross-repo token → comment with what failed and which secret/token policy is required; do not invent credentials.

## Safe outputs

Call at least one of: `create-pull-request`, `add-comment`, or `noop`. A text-only exit with zero safe outputs is a failure.

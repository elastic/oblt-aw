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
  # Labeled only: issue-form labels emit `labeled` after create; `opened` bypasses
  # the compiler's names filter and would run the agent on every new issue.
  issues:
    types: [labeled]
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

## Authoritative procedure (read and follow — do not invent)

**Read and follow** these docs in the workspace; they are the technical contract. Do **not** restate or invent parallel steps.

1. `docs/onboarding/registering-a-repository.md` — required PRs, file shapes, TokenPolicy template, Vault bypassers, secrets, merge ordering, verification.
2. `docs/guides/user/onboard-a-repository.md` — what the human does after registration merges (dashboard enablement).

Use checked-out trees as the docs require (`repos/catalog-info`, `repos/observability-github-settings`, `repos/observability-github-secrets`, and this repo’s root for `elastic/oblt-aw`). Match existing patterns in those trees and under `.github/remote-workflow-template/<org-key>/` when deriving `workflow_ref` values.

## Operating constraints (agent-only)

These are not repeated in the docs; obey them:

- Open **separate** pull requests (one concern each) via `create-pull-request` (`draft: false`). **Do not merge** any PR. Do not close the onboard issue (`auto-close-issue` is already false).
- Before finishing, `add-comment` on the triggering issue with: parsed repository and org-key; checklist of opened/skipped PRs with links; merge order from the registering doc (catalog-info before `elastic/oblt-aw`); that merges are **manual**; pointer to the user guide for post-merge steps.
- Stop conditions: missing/invalid inputs; already registered; permissions/token failures — comment what failed; never invent credentials.
- Call at least one of: `create-pull-request`, `add-comment`, or `noop`. A text-only exit with zero safe outputs is a failure.

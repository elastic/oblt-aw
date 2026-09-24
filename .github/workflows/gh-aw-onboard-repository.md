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
  # No workflow_dispatch: this agent requires the triggering issue for parse/comment.
  issues:
    types: [labeled]
    names: [oblt-aw/onboard/repository]
  roles: [admin, maintainer, write]
  bots:
    - "github-actions[bot]"
concurrency:
  group: ${{ github.workflow }}-onboard-repository-${{ github.event.issue.number }}
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

## Retry safety (before opening PRs)

Before calling `create-pull-request`, search for **existing open** pull requests whose titles start with `[oblt-aw][onboard]` and that target the same `elastic/<repo>` (in any of the allowlisted repos). Prefer GitHub search / `gh pr list` filtered by that title prefix.

Map each matching open PR to one inventory concern by repository (and title):

| Concern | Allowlisted repo | Typical title contains |
|---------|------------------|------------------------|
| catalog | `elastic/catalog-info` | `Add token policy` |
| registration | `elastic/oblt-aw` | `Register` / `active repositories` |
| settings | `elastic/observability-github-settings` | `branch protection` |
| secrets | `elastic/observability-github-secrets` | `secret` / secrets provision |

Then:

1. **Never duplicate** — do not open a second PR for a concern that already has an open matching onboard PR. Do not invent `pulls?q=` search links.
2. **Gap-fill missing concerns** — run [Consumer secrets](#consumer-secrets) (and any other missing inventory steps). If discovery is non-empty and there is **no** open secrets onboard PR for this repository, open that secrets PR. Open other missing always-required concerns the same way when absent.
3. **Stop only when complete** — if every required inventory concern is already covered by open PRs (and secrets is either open or correctly skipped as “none” after full discovery), call `add-comment` with **exact PR URLs**, merge order, and stop.
4. Re-applying the `oblt-aw/onboard/repository` label is the supported retry; treat prior open onboard PRs as the source of truth for concerns they already cover until they merge or close.

## Authoritative procedure (read and follow — do not invent)

**Read and follow** these docs in the workspace. They are the technical contract. Do **not** invent parallel steps.

1. `docs/onboarding/registering-a-repository.md` — especially **Pull request inventory**, **Consumer secrets discovery**, **Automation contract**, **Steps**, and the TokenPolicy appendix.
2. `docs/guides/user/onboard-a-repository.md` — post-merge human steps (dashboard enablement) to cite in the issue comment.

Edit the checked-out trees named in the Automation contract (`repos/catalog-info`, `repos/observability-github-settings`, `repos/observability-github-secrets`, and this repository root for `elastic/oblt-aw`).

### Consumer secrets

Before deciding whether to open a secrets PR (do **not** hardcode secret names):

1. Read `config/<org-key>/workflow-registry.json`.
2. For **every** entry with a `docs:` path, **open that markdown file** and collect consumer-facing secret names from **Prerequisites** first (when the doc says consumers provision/map a name). Fall back to required `Secret:` lines under **API / Interface**.
3. **Union across all registry workflows.** Do **not** filter by `default_enabled`, `enabled_by_default`, “onboarding defaults”, maturity, or whether a workflow is likely to be toggled on later. A secrets PR provisions for the org catalog; dashboard opt-in is separate.
4. In `repos/observability-github-secrets`, resolve each name to a `conf/shared` module (`*.tf` search or README Create Secret table). Fail closed if unresolved — do not invent modules or skip unresolved names.
5. Non-empty set → scaffold or update `conf/resources/<repo>/` (+ `docs/<repo>.md`) and open one secrets PR (`temporary_id` `aw_secrets`). Empty set **only after** the full-union steps above → skip and record “none” in the checklist. Never write “none” because you only inspected default-enabled entries or did not open the docs files.

Follow `docs/onboarding/registering-a-repository.md` (**Consumer secrets discovery**) in full.

### Issue comment links

On each `create-pull-request`, set a distinct `temporary_id` (`aw_catalog`, `aw_obltaw`, `aw_settings`, `aw_secrets` as needed). In the checklist body, link with the same `#aw_…` ids so safe-outputs rewrite them to exact PR URLs. Never invent title-search URLs.

## Safe-output constraints

- Open PRs only via `create-pull-request` (`draft: false`). Do not merge. Do not close the onboard issue.
- Finish with `add-comment` per the Automation contract (checklist with exact PR links, merge order, manual merges, user-guide pointer).
- On failure, comment what failed; never invent credentials.
- Call at least one of: `create-pull-request`, `add-comment`, or `noop`. A text-only exit with zero safe outputs is a failure.

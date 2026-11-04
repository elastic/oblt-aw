---
inlined-imports: true
description: "Approve eligible Observability automerge PRs via pull request review"
imports:
  - gh-aw-fragments/ephemeral-github-token.md
  - gh-aw-fragments/elastic-tools.md
  - gh-aw-fragments/runtime-setup.md
  - gh-aw-fragments/formatting.md
  - gh-aw-fragments/rigor.md
  - gh-aw-fragments/mcp-pagination.md
  - gh-aw-fragments/messages-footer.md
  - gh-aw-fragments/safe-output-submit-review.md
  - gh-aw-fragments/obs-defaults.md
engine:
  id: copilot
  # Required on gh-aw >= v0.91.x: BYOK Copilot disables native web-fetch unless SDK mode is on.
  copilot-sdk: true
  concurrency:
    group: "gh-aw-copilot-${{ github.workflow }}-autoapprove-${{ github.event.pull_request.number }}"
on:
  stale-check: false
  workflow_call:
    inputs:
      additional-instructions:
        description: "Repo-specific instructions appended to the agent prompt"
        type: string
        required: false
        default: ""
      github-token-policy:
        description: "Elastic TokenPolicy id for create-token. When set, mint an OIDC ephemeral token so the review is submitted as the Vault app. Leave empty to use GITHUB_TOKEN."
        type: string
        required: false
        default: ""
    secrets:
      GH_AW_GITHUB_TOKEN:
        required: false
  roles: [admin, maintainer, write]
  # BEGIN synced-from:config/obs/allowed_pr_authors.json:bots
  bots:
    - "dependabot[bot]"
    - "renovate[bot]"
    - "Dependabot"
    - "Renovate"
    - "elastic-renovate-prod[bot]"
    - "elastic-vault-github-plugin-prod[bot]"
    - "github-actions[bot]"
    - "mergify[bot]"
  # END synced-from:config/obs/allowed_pr_authors.json:bots
concurrency:
  group: ${{ github.workflow }}-autoapprove-${{ github.event.pull_request.number }}
  cancel-in-progress: true
# Map workflow_call policy input into the shared ephemeral-token fragment
# (resolves WORKFLOW_TOKEN_POLICY / WORKFLOW_TOKEN_POLICY_CONFIG).
env:
  WORKFLOW_TOKEN_POLICY: ${{ inputs.github-token-policy }}
permissions:
  copilot-requests: write
  actions: read
  contents: read
  issues: read
  pull-requests: read
  id-token: write
tools:
  github:
    # Prefer OIDC create-token output, then MCP/secret fallbacks (gh-aw >= v0.89.21).
    github-token: ${{ steps.create-token.outputs.token || secrets.GH_AW_GITHUB_MCP_SERVER_TOKEN || secrets.GH_AW_GITHUB_TOKEN || secrets.GITHUB_TOKEN }}
    # BEGIN synced-from:config/obs/allowed_pr_authors.json:trusted-users
    trusted-users: "dependabot[bot],renovate[bot],Dependabot,Renovate,elastic-renovate-prod[bot],elastic-vault-github-plugin-prod[bot],github-actions[bot],mergify[bot]"
    # END synced-from:config/obs/allowed_pr_authors.json:trusted-users
    toolsets: [repos, issues, pull_requests, search, actions]
  bash: true
  web-fetch:
safe-outputs:
  activation-comments: false
  # Prefer OIDC create-token output, then secrets (gh-aw >= v0.89.21).
  github-token: ${{ steps.create-token.outputs.token || secrets.GH_AW_GITHUB_TOKEN || secrets.GITHUB_TOKEN }}
strict: false
timeout-minutes: 30
# Approve skips consumer APM shell setup: only PR metadata via MCP is required.
# Do not eval install/build commands outside the agent sandbox with id-token: write.
---

# Automerge autoapprove

Approve pull request #${{ github.event.pull_request.number }} in ${{ github.repository }} when Observability automerge eligibility holds. This workflow is **autoapprove only** — not a general mention-in-PR / chat assistant.

## Context

- **Repository**: ${{ github.repository }}
- **PR**: #${{ github.event.pull_request.number }} — ${{ github.event.pull_request.title }}

This PR already passed automerge validation in the control-plane wrapper (`verify` and dependency collection) for author, label, draft/fork/ref, and collection allow. Re-check the gates below before approving. Do not call check-run or commit status APIs. Required checks are enforced by GitHub at merge time.

## Author allow list

Canonical list (from `config/obs/allowed_pr_authors.json` — do not invent other names):

- `dependabot[bot]`
- `renovate[bot]`
- `Dependabot`
- `Renovate`
- `elastic-renovate-prod[bot]`
- `elastic-vault-github-plugin-prod[bot]`
- `github-actions[bot]`
- `mergify[bot]`

Read the PR author via GitHub MCP (`pull_request_read` or equivalent). Prefer the REST login form. Before comparing any author string to that list, normalize GraphQL `app/<slug>` to `<slug>[bot]` (gh ≥ 2.50 `gh pr view` / pr.json often use the app/ form). Do not use `github.actor` alone — on `labeled` events the actor may be the labeler, not the PR author.

## Approve gates

Approve the PR only when **all** of these are true:

- Normalized PR author is in the canonical allow list above
- PR has label `oblt-aw/ai/merge-ready`
- PR is not draft
- PR is not from a fork (head repo equals base repo)
- Head ref is different from base ref

## Actions

When all gates are true, you MUST call `submit_pull_request_review` with `event=APPROVE`.
Do not use `event=COMMENT` to report eligibility success; COMMENT is not an approval.
If any gate is false, do not approve, do not request changes, and do not submit a review that claims eligibility.
Keep output minimal. Do not leave inline review comments. Do not push code. Do not merge.

${{ inputs.additional-instructions }}

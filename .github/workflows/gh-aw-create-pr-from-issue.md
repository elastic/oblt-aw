---
inlined-imports: true
name: "Create PR From Issue"
description: "Implement an issue and open a pull request"
imports:
  - gh-aw-fragments/elastic-tools.md
  - gh-aw-fragments/runtime-setup.md
  - gh-aw-fragments/formatting.md
  - gh-aw-fragments/rigor.md
  - gh-aw-fragments/mcp-pagination.md
  - gh-aw-fragments/workflow-edit-guardrails.md
  - gh-aw-fragments/messages-footer.md
  - gh-aw-fragments/playwright-mcp-explorer.md
  - gh-aw-fragments/safe-output-add-comment-issue.md
  - gh-aw-fragments/safe-output-create-pr.md
  - gh-aw-fragments/network-ecosystems.md
  - gh-aw-fragments/obs-defaults.md
engine:
  id: copilot
  concurrency:
    group: "gh-aw-copilot-${{ github.workflow }}-create-pr-from-issue-${{ inputs.target-issue-number }}"
  # Wider than defaults so short Copilot CAPI 502 / proxy outages can clear
  # without abandoning the PR stage after an audit issue was already filed.
  # Note: with compiler v0.87.10 this also applies to threat-detection (nested
  # threat-detection.engine.harness is not supported yet). Detection only runs
  # after the agent produces output and is continue-on-error.
  harness:
    max-retries: 6
    initial-delay-ms: 30000
    backoff-multiplier: 2
    max-delay-ms: 180000
on:
  stale-check: false
  workflow_call:
    inputs:
      target-issue-number:
        description: "Issue number to implement"
        type: string
        required: true
      additional-instructions:
        description: "Repo-specific instructions appended to the agent prompt"
        type: string
        required: false
        default: ""
    secrets:
      EXTRA_COMMIT_GITHUB_TOKEN:
        required: false
  roles: [admin, maintainer, write]
  bots:
    - "github-actions[bot]"
concurrency:
  group: ${{ github.workflow }}-create-pr-from-issue-${{ inputs.target-issue-number }}
  cancel-in-progress: true
permissions:
  copilot-requests: write
  actions: read
  contents: read
  issues: read
  pull-requests: read
tools:
  github:
    toolsets: [repos, issues, pull_requests, search, actions]
  bash: true
  web-fetch:
strict: false
safe-outputs:
  activation-comments: false
  # Also listed in obs-defaults; gh-aw v0.88.7 does not merge report-failed-jobs from imports.
  report-failed-jobs: false
  max-patch-size: 10240
  add-comment:
    max: 1
    pull-requests: false
    issues: true
    discussions: false
    target: "${{ inputs.target-issue-number }}"
  create-pull-request:
    # Top-level mapping shadows imported safe-output-create-pr.md; keep draft,
    # patch-format, and extra-commit token here so the compiled lock retains them
    # (no draft-prs lock input).
    draft: false
    patch-format: bundle
    github-token-for-extra-empty-commit: ${{ secrets.EXTRA_COMMIT_GITHUB_TOKEN }}
    # Exclusive allowlist: every changed path must match (orthogonal to protected-files).
    allowed-files:
      - "*.md"
      - "**/*.md"
      - "*.adoc"
      - "**/*.adoc"
      - "*.asciidoc"
      - "**/*.asciidoc"
      - "*.rst"
      - "**/*.rst"
    protected-files:
      # Compiler v0.88.7 schema uses underscore; hyphen form is docs-only alias in newer docs.
      policy: request_review
      exclude:
        - README.md
        - CONTRIBUTING.md
        - SECURITY.md
        - CODE_OF_CONDUCT.md
timeout-minutes: 90
---

# Create PR From Issue

Implement issue #${{ inputs.target-issue-number }} on ${{ github.repository }} and open a pull request.

## Context

- **Repository**: ${{ github.repository }}
- **Issue**: #${{ inputs.target-issue-number }}

## Constraints

- **CAN**: Read files, search code, modify files locally, run tests and commands, comment on the targeted issue, create pull requests
- **CANNOT**: Directly push or commit to the repository — use `ready_to_make_pr` then `create_pull_request` to propose changes

## Autodoc documentation fix (Observability)

Your task is to implement the documentation improvements described in the issue.

### Pull Request Requirements

- Title: `docs: Documentation analysis and improvement`
- Body must include:
  - A plain reference to the target issue near the top (for example `Related issue: #<issue-number>` or `elastic/<repo>#<issue-number>`). Safe-output **neutralizes** closing keywords such as `Closes #…` / `Fixes #…`, so do **not** rely on those for auto-close; humans can close the audit issue after review.
  - Summary of files analyzed
  - List of issues found (with file paths and concise descriptions)
  - List of changes made (with rationale for each change)
- Open the pull request **ready for review** (not draft). Humans still review before merge; do not merge.

### Constraints

- Do not modify source code, workflow logic, scripts, or data files — only documentation files.
- Do not create new workflow YAML files.
- Prefer targeted, high-confidence improvements over speculative rewrites.
- All changes must be grounded in actual repository content — do not invent capability descriptions.
- Do not add placeholder text or TODOs as improvements.

### Secret documentation

When implementing documentation related to secret definitions or usage, follow the Observability org rules encoded here. Do **not** attempt to read private repositories (including [`elastic/observability-github-secrets`](https://github.com/elastic/observability-github-secrets)) via GitHub tools or MCP. Do not add guidance that contradicts these rules or invent process beyond them and what is already documented in the target repository:

- Prefer ephemeral GitHub tokens (`elastic/oblt-actions/github/create-token`) and catalog TokenPolicy over long-lived repository secrets when that pattern applies.
- Do not recommend provisioning secrets only via GitHub **Settings → Secrets** unless the repository's own docs already document that exception.
- When long-lived Action secrets are required, tell readers to provision them through [`elastic/observability-github-secrets`](https://github.com/elastic/observability-github-secrets) per org process; do not invent alternate provisioning procedures.
- Use exact secret names from the repository's workflow documentation when present; do not invent secret names or procedures.

### Markdown tables

Preserve deliberate cell content such as a leading `-` used as an icon or status placeholder; do not rewrite table rows into bullet lists or "clean up" punctuation unless it is clearly a mistake.

### Markdown link fragments / anchors

When editing markdown links with `#fragment`, first validate the fragment against the target document heading slug(s). Preserve the existing fragment unless verification proves it is incorrect. Do not remove a leading `-` when it is part of the valid computed slug (for example icon-prefixed headings): the `-` character is a valid replacement for a leading icon in heading text and therefore a valid part of the anchor slug. Rewriting `[Lab 01: Troubleshooting](01-installation-setup.md#-troubleshooting-quick-reference)` to `[Lab 01: Troubleshooting](01-installation-setup.md#troubleshooting-quick-reference)` is invalid when the verified heading slug is `#-troubleshooting-quick-reference`.

### Auto-generated docs

Skip hand-editing any file that is obviously generated or regenerated by tooling. If the issue asks for edits there, leave those files unchanged (this job is docs-only) and note in the PR body what generator, template, automation, or out-of-repo follow-up would be needed; apply any safe changes only to human-maintained documentation files permitted above.

### Legacy / historical comments

When updating prose near inline comments that document past context or rationale, keep those comments when they remain true or still help readers understand edge cases; prefer minimal edits or a brief clarification over deleting long-standing context solely for brevity.

### AI assets / agent configuration files

Never modify AI-related assets in this workflow. AI assets, skills files, instruction/configuration files, and lock files (for example `*.lock*` and `*.lock.yml`) are always out of scope.

### Helm chart internals

Never modify Helm chart internal files. Template files (`helm-charts/**/templates/**`), notes files (`helm-charts/**/NOTES.txt`), and markdown files under `helm-charts/` are always out of scope.

### Repository autodoc ignore file

When `.oblt-aw.autodocignore` exists at the repository root, treat its patterns with `.gitignore` (gitwildmatch) semantics. Never modify paths that match those patterns, even when an issue requests it; note any skipped items in the PR body. Active patterns from that file are appended to these instructions at runtime when present.

## Instructions

1. Read issue #${{ inputs.target-issue-number }} first to understand requirements and acceptance criteria.
2. Investigate the relevant documentation paths and implement a focused docs-only fix for the issue.
3. Run required repo checks (lint/build/test) relevant to your change when applicable. If required commands cannot run, explain why and do not open a PR.
4. Call `ready_to_make_pr` and apply its checklist.
5. Call `create_pull_request` with the required title/body that references issue #${{ inputs.target-issue-number }} (plain link — not a neutralized `Closes`/`Fixes` keyword).
6. If implementation is blocked or unclear, call `add_comment` on the issue with a concise status update and concrete next step.

${{ inputs.additional-instructions }}

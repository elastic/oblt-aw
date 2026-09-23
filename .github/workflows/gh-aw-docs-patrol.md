---
inlined-imports: true
description: "Detect code changes that require documentation updates and file issues"
imports:
  - gh-aw-fragments/elastic-tools.md
  - gh-aw-fragments/formatting.md
  - gh-aw-fragments/messages-footer.md
  - gh-aw-fragments/mcp-pagination.md
  - gh-aw-fragments/network-ecosystems.md
  - gh-aw-fragments/obs-defaults.md
  - gh-aw-fragments/ensure-full-history.md
  - gh-aw-fragments/previous-findings.md
  - gh-aw-fragments/pick-three-keep-many.md
  - gh-aw-fragments/rigor.md
  - gh-aw-fragments/runtime-setup.md
  - gh-aw-fragments/safe-output-create-issue.md
  - gh-aw-fragments/scheduled-audit.md
engine:
  id: copilot
on:
  stale-check: false
  workflow_call:
    inputs:
      additional-instructions:
        description: "Repo-specific instructions appended to the agent prompt"
        type: string
        required: false
        default: ""
  roles: [admin, maintainer, write]
  bots:
    - "github-actions[bot]"
concurrency:
  group: ${{ github.workflow }}-docs-patrol
  cancel-in-progress: true
permissions:
  copilot-requests: write
  actions: read
  contents: read
  issues: read
  pull-requests: read
tools:
  github:
    toolsets: [repos, issues, pull_requests, search]
  bash: true
  web-fetch:
strict: false
safe-outputs:
  activation-comments: false
  # Also listed in obs-defaults; gh-aw v0.88.7 does not merge report-failed-jobs from imports.
  report-failed-jobs: false
  create-issue:
    max: 1
    title-prefix: "[oblt-aw][autodoc] "
    close-older-key: "[oblt-aw][autodoc]"
    close-older-issues: false
    expires: 7d
timeout-minutes: 90
---

Detect documentation drift — code changes that require corresponding documentation updates — and documentation gaps that leave the repository incompletely or incorrectly documented.

### Precedence

1. Start from the lookback commit window and docs inventory below (docs-patrol).
2. Apply Observability gap criteria, secret-docs rules, and false-positive / out-of-scope guards when deciding what to file.
3. Prefer noop unless findings clear the quality gate.
4. Do **not** drive discovery by searching the open-issue backlog. Audit from commits + documentation inventory. Still skip a finding when an open issue or PR already tracks that specific documentation update.

### Data Gathering

Use a lookback window of `--since="1 day ago"` for all runs (scheduled and manual).

1. Run `git log --since="1 day ago" --oneline --stat` to get a summary of recent commits. If there are no commits in the lookback window, report no findings and stop.
2. Discover documentation files dynamically — scan the repository for common doc locations: `README.md`, `CONTRIBUTING.md`, `DEVELOPING.md`, `docs/`, `documentation/`, and any `.md` files in the repository root. Do not assume a fixed directory structure.

### What to Look For — Commit drift

For each commit (or group of related commits), determine whether the changes could require documentation updates. Focus on:

1. **Public API changes** — new, renamed, or removed functions, endpoints, CLI flags, configuration options, or workflow inputs/outputs
2. **Behavioral changes** — altered defaults, changed error messages, modified control flow that affects user-facing behavior
3. **New features or workflows** — anything a user or contributor would need to know about
4. **Dependency or tooling changes** — version bumps, new dependencies, changed build/test commands
5. **Structural changes** — moved, renamed, or deleted files that are referenced in documentation
6. **Configuration changes** — new environment variables, changed file formats, altered directory structures

### What to Look For — Documentation gaps

When reviewing the docs inventory (and code touched in the lookback window), also consider these gaps in priority order:

1. **Undocumented or partially documented code** — features, scripts, workflows, or configuration files that are not covered (or only partially covered) in the repository's documentation; for each gap found, specify which files to add or expand to describe purpose, parameters, behavior, and usage examples
2. **Empty or missing files** — files that exist but contain no meaningful content
3. **Missing sections** — key README sections absent such as purpose, usage, inputs, outputs, examples, or contributing guidance
4. **Outdated content** — references to components, configurations, or capabilities no longer present or not yet documented
5. **Incomplete descriptions** — sections that exist but lack meaningful detail (stubs, TODOs, placeholder text)
6. **Broken cross-references** — links to files, workflows, or sections that do not exist in the repository
7. **Inconsistencies** — documentation that contradicts the actual source files in the repository

### Parallel Analysis

Use the **Pick Three, Keep Many** pattern for the analysis: spawn 3 `general-purpose` sub-agents, each analyzing the recent commits and docs inventory from a different angle (e.g., one checking public API and behavioral changes, one checking structural and configuration changes, one checking documentation gaps and dependency updates). Include the git log output, commit diffs, documentation file inventory, and the full "What to Look For" / "What to Skip" criteria in each sub-agent prompt. Each sub-agent should return all findings that meet the quality criteria.

### How to Analyze

For each potentially impactful change or gap:
- Read the full diff to understand what changed (when commit-driven)
- Read the current documentation files to understand what's documented
- Check whether the relevant documentation was already updated in the same commit or a subsequent commit within the lookback window
- Check whether an open issue or PR already tracks the documentation update (skip if so; do not use issue search as the primary discovery method)

### What to Skip

- Purely internal refactors with no user-facing impact
- Changes where documentation was already updated in the same or a later commit
- Changes where an open issue or PR already tracks the documentation update
- Test-only changes
- Minor changes where the existing docs are still substantially correct (e.g., a new optional parameter with a sensible default)
- Changes that only affect internal implementation details not referenced in any documentation
- **Markdown tables** — A leading `-` (or similar punctuation) inside a table cell can be intentional (for example as a lightweight icon or status marker, not a broken nested list). Do not flag these as formatting defects unless you can show they break rendering or contradict repository conventions.
- **Markdown link fragments / anchors** — Preserve existing link fragments (the `#...` part) unless heading verification proves a correction is required. Do not “normalize” anchors based on style preferences alone. This includes icon-prefixed headings where the computed slug intentionally starts with `-`: the `-` character is a valid replacement for a leading icon in the heading text and therefore a valid part of the anchor slug. For example, rewriting `[Lab 01: Troubleshooting](01-installation-setup.md#-troubleshooting-quick-reference)` to `[Lab 01: Troubleshooting](01-installation-setup.md#troubleshooting-quick-reference)` is invalid when the verified heading slug is `#-troubleshooting-quick-reference`.
- **Auto-generated documentation** — Files produced or overwritten by generators, templates, or sync jobs (banners such as “do not edit”, “generated by”, `AUTO-GENERATED`, paths listed only in codegen output, etc.) should not be the target of hand-edited “doc fixes”. Instead, call out the real source (script, template, OpenAPI/spec, upstream package) or the automation that should change, or state that the fix belongs outside the repo.
- **Legacy inline comments** — Comments that explain past incidents, migrations, or non-obvious rationale may still be worth keeping for context even when nearby prose is refreshed. Prefer “update in place” or a short clarifying suffix over recommending deletion when the history remains accurate or useful.
- **AI assets / agent configuration files** — Do not propose changes to AI-related assets. Treat AI assets, skills files, instruction/configuration files, and lock files (for example `*.lock*` and `*.lock.yml`) as strictly out of scope for autodoc findings.
- **Helm chart internals** — Do not propose changes to Helm chart internal files. Treat template files (`helm-charts/**/templates/**`), notes files (`helm-charts/**/NOTES.txt`), and any markdown files under `helm-charts/` as strictly out of scope for autodoc findings.
- **Repository autodoc ignore file** — When `.oblt-aw.autodocignore` exists at the repository root, treat its patterns with `.gitignore` (gitwildmatch) semantics. Never propose documentation findings that require editing ignored paths. Active patterns from that file are appended to these instructions at runtime when present.

### Secret documentation

When proposing documentation about secret definitions or usage, follow the Observability org rules encoded here. Do **not** attempt to read private repositories (including [`elastic/observability-github-secrets`](https://github.com/elastic/observability-github-secrets)) via GitHub tools or MCP. Ground secret-related findings only in these rules and in what is already documented in the target repository:

- Prefer ephemeral GitHub tokens (`elastic/oblt-actions/github/create-token`) and catalog TokenPolicy over long-lived repository secrets when that pattern applies.
- Do not recommend provisioning secrets only via GitHub **Settings → Secrets** unless the repository's own docs already document that exception.
- When long-lived Action secrets are required, tell readers to provision them through [`elastic/observability-github-secrets`](https://github.com/elastic/observability-github-secrets) per org process; do not invent alternate provisioning procedures.
- Use exact secret names from the repository's workflow documentation when present; do not invent secret names or procedures.

### Quality Gate — When to Noop

**Noop is the expected outcome most days.** Only file an issue when:
- The documentation is **concretely wrong** — a user following the docs would get incorrect results or errors
- A **new public feature** has zero documentation
- A **removed or renamed** public interface is still referenced in docs
- A documentation gap from the gap criteria above is concrete enough that a contributor would be misled or blocked

Do not file for: vague "could be improved" suggestions, minor wording drift, or documentation that is slightly imprecise but still functionally correct.

### Issue Format

**Issue title:** Brief summary of what's out of date (e.g., "Update README for new CLI flag")

**Team discovery:** Safe-output issue bodies neutralize `@mentions` (they are backticked and do not notify). Do not rely on `@elastic/observablt-ci` for alerts. Use the baked title prefix `[oblt-aw][autodoc]` and concrete file paths so the team can find and triage issues.

**Issue body:**

> Recent code changes in the repository have introduced documentation drift. The following changes need corresponding documentation updates.
>
> ## Changes Requiring Documentation Updates
>
> ### 1. [Brief description of the change]
>
> **Source path(s):** [exact repository path(s) that need documentation — required]
> **Commit(s):** [SHA(s) with links]
> **What changed:** [Concise description of the code change]
> **Documentation impact:** [Which doc file(s) need updating and what specifically needs to change]
>
> ### 2. [Next change...]
>
> ## Suggested Actions
>
> - [ ] [Specific, actionable checkbox for each documentation update needed — reference file paths and describe the change]

For each finding, include a clear, actionable checklist of specific documentation changes to make. Each item must reference exact source file paths and describe the change needed.

${{ inputs.additional-instructions }}

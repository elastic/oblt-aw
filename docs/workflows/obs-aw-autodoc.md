# Workflow: `obs-aw-autodoc.yml`

## Overview

Source file: [.github/workflows/obs-aw-autodoc.yml](../../.github/workflows/obs-aw-autodoc.yml)

This reusable workflow automates documentation maintenance in two stages: audit for documentation drift, then open a docs-only PR when findings exist.

Landing home for the audit primitive (under [#2052](https://github.com/elastic/oblt-aw/issues/2052) / [#1876](https://github.com/elastic/oblt-aw/issues/1876)): **`elastic/oblt-aw`**.

## Prerequisites

- Triggered via `workflow_call`.

## Usage

Jobs:

- `audit`: calls the Observability-owned `gh-aw-docs-patrol.lock.yml` to analyze docs and create an issue with actionable findings. Created issues always @mention `@elastic/observablt-ci` in the body so the team receives notifications.
- `fix`: calls `gh-aw-create-pr-from-issue.lock.yml` only when `audit` created an issue (still upstream until [#2053](https://github.com/elastic/oblt-aw/issues/2053)).
- `audit` failure reporting is baked into the in-repo lock via [`obs-defaults.md`](../../.github/workflows/gh-aw-fragments/obs-defaults.md) (no `report-failure-as-issue` lock input). `fix` still sets `report-failure-as-issue: false` on the upstream create-PR lock. Intentional findings from `create_issue` (audit) are unchanged.
- `finalize-pr`: requests a review from `@elastic/observablt-ci` and applies the `changelog:docs` label to the created PR if that label exists in the repository.
- `notify-fix-failure`: when `fix` fails after an audit issue was created, comments recovery guidance on that issue (including `/ai implement`) and applies `oblt-aw/autodoc/fix-failed` when that label exists in the repository.

The job `audit` calls:

```yaml
uses: elastic/oblt-aw/.github/workflows/gh-aw-docs-patrol.lock.yml@main
```

Edit the GH-AW source [`.github/workflows/gh-aw-docs-patrol.md`](../../.github/workflows/gh-aw-docs-patrol.md) and compile with `make compile-aw-check` from the repository root (do not hand-edit the lock).

### Opinionated vs preserved

| Opinionated (Observability-owned) | Preserved as lock inputs |
|-----------------------------------|--------------------------|
| Model, failure-issue suppression, and GitHub `trusted-users` via [`obs-defaults.md`](../../.github/workflows/gh-aw-fragments/obs-defaults.md) | `additional-instructions` (from `aw-resolve-agentic-assets`) |
| Lookback window (`1 day ago`) and issue title prefix (`[oblt-aw][autodoc]`) hardcoded on the source | |
| Comment footer via [`messages-footer.md`](../../.github/workflows/gh-aw-fragments/messages-footer.md) | |
| Bot actor hardcoded on the source (`github-actions[bot]`) | |

Workflow-specific requirements passed to the PR stage:

- PR title must be `docs: Documentation analysis and improvement`
- PR body must include analyzed files, issues found, and changes made
- only documentation files may be changed

Additional guidance encoded in `additional-instructions` for both audit and fix jobs:

- **Secret documentation:** Audit and fix stages use distilled Observability org rules in `platform-additional-instructions` (prefer ephemeral tokens / catalog TokenPolicy; do not default to GitHub **Settings → Secrets**; when long-lived secrets are required, point readers at [`elastic/observability-github-secrets`](https://github.com/elastic/observability-github-secrets) for provisioning; use exact secret names from workflow docs). The agent must **not** attempt to read that private repository via GitHub tools or MCP. These rules align with [Configure a GitHub secret](../guides/operator/configure-a-github-secret.md).
- Treat leading `-` (and similar) in **table cells** as potentially intentional (for example icon or status placeholders); avoid “cleaning” them without evidence of a real defect.
- Preserve existing markdown link fragments (`#...`) unless target-heading verification proves a correction is required; when editing links with fragments, validate against the target heading slug first. This includes icon-prefixed headings where the valid slug starts with `-`: the `-` character is a valid replacement for a leading icon in heading text and therefore a valid part of the anchor slug (for example, changing `[Lab 01: Troubleshooting](01-installation-setup.md#-troubleshooting-quick-reference)` to `[Lab 01: Troubleshooting](01-installation-setup.md#troubleshooting-quick-reference)` is invalid when the verified slug is `#-troubleshooting-quick-reference`).
- Do not hand-edit **auto-generated** documentation in the fix PR (docs-only); the audit should steer fixes toward generators, templates, or other sources of truth, and the PR body should record any follow-up that is outside this workflow’s scope.
- Preserve or lightly refresh **legacy inline comments** that still document useful context or history; avoid deleting them only for brevity.
- AI-related files are always out of scope for autodoc changes: AI assets, skills files, instruction/configuration files, and lock files (for example `*.lock*` and `*.lock.yml`).
- Helm chart internal files are always out of scope for autodoc changes: template files (`helm-charts/**/templates/**`), notes files (`helm-charts/**/NOTES.txt`), and markdown files under `helm-charts/`.
- When `.oblt-aw.autodocignore` exists at the repository root, patterns in that file use `.gitignore` (gitwildmatch) semantics. The audit must not propose findings that require editing ignored paths; the fix stage must not modify ignored paths. Active patterns are appended to agent instructions at runtime by `aw-resolve-agentic-assets`.

## Configuration

Permissions:

- `actions: read`
- `contents: write`
- `discussions: write`
- `issues: write`
- `pull-requests: write`

`notify-fix-failure` uses job-level `issues: write` only.

## Cutover and rollback

**Cutover:** the wrapper `audit` job `uses` `elastic/oblt-aw/.../gh-aw-docs-patrol.lock.yml@main` instead of `elastic/ai-github-actions/...@main`. Schedule routing and resolve inputs are unchanged; the lock interface is reduced to `additional-instructions` only.

**Rollback:** point the wrapper audit job back at the previous upstream lock:

```yaml
uses: elastic/ai-github-actions/.github/workflows/gh-aw-docs-patrol.lock.yml@main
with:
  lookback-window: 1 day ago
  title-prefix: "[oblt-aw][autodoc]"
  additional-instructions: ${{ needs.resolve-apm-assets-audit.outputs.resolved-additional-instructions }}
  report-failure-as-issue: false
```

Copies in `elastic/ai-github-actions` remain for other consumers; this cutover does not deprecate or remove them.

**E2E:** production schedule-path validation for the audit stage lives under [autodoc-e2e](../testing/autodoc-e2e.md) ([#2052](https://github.com/elastic/oblt-aw/issues/2052)). Manual `workflow_dispatch` via [`.github/workflows/e2e-autodoc.yml`](../../.github/workflows/e2e-autodoc.yml); not a default PR required gate.

## References

- Routing rules: [docs/routing/autodoc-routing.md](../routing/autodoc-routing.md)
- In-repo source: [`.github/workflows/gh-aw-docs-patrol.md`](../../.github/workflows/gh-aw-docs-patrol.md)
- In-repo lock: [`.github/workflows/gh-aw-docs-patrol.lock.yml`](../../.github/workflows/gh-aw-docs-patrol.lock.yml)
- Shared model defaults: [`.github/workflows/gh-aw-fragments/obs-defaults.md`](../../.github/workflows/gh-aw-fragments/obs-defaults.md)
- Prior upstream (rollback / other consumers): [elastic/ai-github-actions](https://github.com/elastic/ai-github-actions) — `gh-aw-docs-patrol`
- E2E harness: [autodoc-e2e](../testing/autodoc-e2e.md)

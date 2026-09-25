# Workflow: `obs-aw-autodoc.yml`

## Overview

Source file: [.github/workflows/obs-aw-autodoc.yml](../../.github/workflows/obs-aw-autodoc.yml)

This reusable workflow automates documentation maintenance in two stages: audit for documentation drift, then open a docs-only PR when findings exist.

Landing home for the audit and fix primitives (under [#2052](https://github.com/elastic/oblt-aw/issues/2052) / [#2053](https://github.com/elastic/oblt-aw/issues/2053) / [#1876](https://github.com/elastic/oblt-aw/issues/1876)): **`elastic/oblt-aw`**.

## Prerequisites

- Triggered via `workflow_call`.

## Usage

Jobs:

- `audit`: calls the Observability-owned `gh-aw-docs-patrol.lock.yml` to analyze docs and create an issue with actionable findings. Safe-output issue bodies neutralize `@mentions`; triage uses the baked `[oblt-aw][autodoc]` title prefix and concrete source paths.
- `fix`: calls the Observability-owned `gh-aw-create-pr-from-issue.lock.yml` only when `audit` created an issue.
- Failure meta-issue suppression for both stages is baked into the in-repo locks via [`obs-defaults.md`](../../.github/workflows/gh-aw-fragments/obs-defaults.md) (no `report-failure-as-issue` lock input). Intentional findings from `create_issue` (audit) are unchanged.
- `finalize-pr`: requests a review from `@elastic/observablt-ci` and applies the `changelog:docs` label to the created PR if that label exists in the repository.
- `notify-fix-failure`: when `fix` fails after an audit issue was created, comments recovery guidance on that issue (including `/ai implement`) and applies `oblt-aw/autodoc/fix-failed` when that label exists in the repository.
- `notify-no-pr`: when `fix` succeeds with an empty `created_pr_number`, comments recovery guidance on the audit issue (same pattern as issue/security/RNAI fixers).

The job `audit` calls:

```yaml
uses: elastic/oblt-aw/.github/workflows/gh-aw-docs-patrol.lock.yml@main
```

The job `fix` calls:

```yaml
uses: elastic/oblt-aw/.github/workflows/gh-aw-create-pr-from-issue.lock.yml@main
```

Edit the GH-AW sources [`.github/workflows/gh-aw-docs-patrol.md`](../../.github/workflows/gh-aw-docs-patrol.md) and [`.github/workflows/gh-aw-create-pr-from-issue.md`](../../.github/workflows/gh-aw-create-pr-from-issue.md) and compile with `make compile-aw-check` from the repository root (do not hand-edit the locks).

### Opinionated vs preserved

| Opinionated (Observability-owned) | Preserved as lock inputs |
|-----------------------------------|--------------------------|
| Model, failure-issue suppression, and GitHub `trusted-users` via [`obs-defaults.md`](../../.github/workflows/gh-aw-fragments/obs-defaults.md) | Audit/fix: `additional-instructions` (from `aw-resolve-agentic-assets`: APM + `.oblt-aw.autodocignore` overlays; optional E2E `e2e-additional-instructions` as platform text) |
| Lookback window (`1 day ago`), issue title prefix (`[oblt-aw][autodoc]`), and merged audit prompt in [`gh-aw-docs-patrol.md`](../../.github/workflows/gh-aw-docs-patrol.md) | Fix: `target-issue-number` (from `audit.outputs.created_issue_number`) |
| Docs-only fix prompt, draft PRs, and top-level docs `protected-files` excludes in [`gh-aw-create-pr-from-issue.md`](../../.github/workflows/gh-aw-create-pr-from-issue.md) | Optional schedule `e2e-additional-instructions` (empty for normal runs; live E2E only) |
| Comment footer via [`messages-footer.md`](../../.github/workflows/gh-aw-fragments/messages-footer.md) | |
| Bot actor hardcoded on each source (`github-actions[bot]`) | |

**Audit prompt:** docs-patrol lookback/drift analysis plus Observability gap criteria, secret-docs rules, false-positive / out-of-scope guards, and mandatory `@elastic/observablt-ci` issue notification live in [`gh-aw-docs-patrol.md`](../../.github/workflows/gh-aw-docs-patrol.md). The wrapper does not pass audit `platform-additional-instructions`.

**Fix prompt:** PR title/body rules, docs-only constraints, secret-docs rules, markdown/Helm/AI-asset guards, and autodocignore semantics live in [`gh-aw-create-pr-from-issue.md`](../../.github/workflows/gh-aw-create-pr-from-issue.md). The wrapper does not pass fix `platform-additional-instructions`; resolve still supplies APM / autodocignore overlays via `additional-instructions`.

**Protected-files excludes (fix):** the compiled create-PR lock keeps `request_review` for remaining protected paths, and **excludes** these common top-level docs from the protected set so autodoc can push PRs that update them instead of falling back to a review issue:

- `README.md`
- `CONTRIBUTING.md`
- `SECURITY.md`
- `CODE_OF_CONDUCT.md`

Do **not** use `protected-files: allowed` on this route (that would unlock manifests, `.github/`, and agent instruction files).

## Configuration

Permissions:

- `actions: read`
- `contents: write`
- `discussions: write`
- `issues: write`
- `pull-requests: write`

`notify-fix-failure` and `notify-no-pr` use job-level `issues: write` only.

## Cutover and rollback

**Cutover:**

- Wrapper `audit` uses `elastic/oblt-aw/.../gh-aw-docs-patrol.lock.yml@main`.
- Wrapper `fix` uses `elastic/oblt-aw/.../gh-aw-create-pr-from-issue.lock.yml@main` with only `target-issue-number` and `additional-instructions`.

**Rollback (fix):** point the wrapper fix job back at the previous upstream lock:

```yaml
uses: elastic/ai-github-actions/.github/workflows/gh-aw-create-pr-from-issue.lock.yml@main
with:
  target-issue-number: ${{ needs.audit.outputs.created_issue_number }}
  draft-prs: true
  additional-instructions: ${{ needs.resolve-apm-assets-fix.outputs.resolved-additional-instructions }}
  report-failure-as-issue: false
```

Copies in `elastic/ai-github-actions` remain for other consumers; this cutover does not deprecate or remove them.

**E2E:** production schedule-path validation for audit and fix stages lives under [autodoc-e2e](../testing/autodoc-e2e.md) ([#2052](https://github.com/elastic/oblt-aw/issues/2052), [#2053](https://github.com/elastic/oblt-aw/issues/2053)). Manual `workflow_dispatch` via [`.github/workflows/e2e-autodoc.yml`](../../.github/workflows/e2e-autodoc.yml); not a default PR required gate.

## References

- Routing rules: [docs/routing/autodoc-routing.md](../routing/autodoc-routing.md)
- In-repo audit source: [`.github/workflows/gh-aw-docs-patrol.md`](../../.github/workflows/gh-aw-docs-patrol.md)
- In-repo fix source: [`.github/workflows/gh-aw-create-pr-from-issue.md`](../../.github/workflows/gh-aw-create-pr-from-issue.md)
- Shared model defaults: [`.github/workflows/gh-aw-fragments/obs-defaults.md`](../../.github/workflows/gh-aw-fragments/obs-defaults.md)
- Prior upstream (rollback / other consumers): [elastic/ai-github-actions](https://github.com/elastic/ai-github-actions) — `gh-aw-docs-patrol`, `gh-aw-create-pr-from-issue`
- E2E harness: [autodoc-e2e](../testing/autodoc-e2e.md)
- Protected files reference: [GH-AW safe outputs (pull requests)](https://github.com/github/gh-aw/blob/main/docs/src/content/docs/reference/safe-outputs-pull-requests.md)

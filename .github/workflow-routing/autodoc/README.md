# Autodoc routing

This folder documents routing and operational notes for the documentation improvement capability.

## Entrypoint route

`oblt-aw-ingress.yml` dispatches to `gh-aw-autodoc.yml` when:

- event is `schedule`

No additional inputs or capability flags are required; scheduling is the only trigger.

## Routed workflow

- `schedule` -> `gh-aw-autodoc.yml`

## Workflow flow

`gh-aw-autodoc.yml` runs an issue-first two-step flow:

1. **`audit` (always runs):** Calls `gh-aw-docs-patrol.lock.yml` from `elastic/ai-github-actions`. Audits all repository documentation for gaps, outdated content, and inconsistencies; creates an issue with concrete findings when drift is detected. The issue title is prefixed with `[oblt-aw][autodoc]` and `@elastic/observablt-ci` is always mentioned.
2. **`fix` (conditional):** Calls `gh-aw-create-pr-from-issue.lock.yml` from `elastic/ai-github-actions`. Runs only when `audit` created an issue (`audit` output `created_issue_number` is non-empty). Implements the audit findings and opens a draft PR for review; does **not** merge automatically.

## Notes

- Only documentation files are modified by the `fix` step; source code, workflow logic, scripts, and data files are left untouched.
- Draft PRs are opened by `fix`; they must be manually promoted to ready-for-review before merging.

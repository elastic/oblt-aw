---
model: gpt-5.3-codex
safe-outputs:
  report-failure-as-issue: false
  report-failed-jobs: false
  noop:
    report-as-issue: false
  missing-tool:
    create-issue: false
  missing-data:
    create-issue: false
  report-incomplete:
    create-issue: false
tools:
  github:
    min-integrity: approved
    trusted-users: "github-actions[bot]"
---

## Observability defaults

Shared opinionated defaults for Observability-owned agentic workflows. Import this fragment from each in-repo `gh-aw-*.md` so model, failure reporting, and trusted users stay in one place.

Failure reporting: `report-failure-as-issue` and `report-failed-jobs` are off, and every default failure fallback that can open a tracking issue is set to `create-issue: false` / `report-as-issue: false` (`noop`, `missing-tool`, `missing-data`, `report-incomplete`). Keep those signals for run handling; do not open new issues.

Note: `on.bots` cannot be declared in a shared fragment; pin bot actors on each workflow that needs them (for example `github-actions[bot]` and `buildkite-limited-access[bot]`).

Note: as of gh-aw v0.88.7, `report-failed-jobs` is not merged from imports into the main workflow `safe-outputs` — repeat it on each importing `gh-aw-*.md` until the compiler merges that meta field. Do not declare a bare `noop:` on the main workflow; that overrides this fragment and restores `report-as-issue: true`.

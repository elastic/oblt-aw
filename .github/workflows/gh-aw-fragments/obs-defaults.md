---
model: gpt-5.3-codex
safe-outputs:
  report-failure-as-issue: false
tools:
  github:
    min-integrity: approved
    trusted-users: "github-actions[bot]"
---

## Observability defaults

Shared opinionated defaults for Observability-owned agentic workflows. Import this fragment from each in-repo `gh-aw-*.md` so model, failure reporting, and trusted users stay in one place.

Note: `on.bots` cannot be declared in a shared fragment; pin bot actors on each workflow that needs them (for example `github-actions[bot]` and `buildkite-limited-access[bot]`).

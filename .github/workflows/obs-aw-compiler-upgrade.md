---
inlined-imports: true
name: "Compiler Upgrade Check"
description: "Check .aw-compiler-version against gh-aw releases and open an issue only when an actionable upgrade exists"
imports:
  - gh-aw-fragments/obs-defaults.md
  - gh-aw-fragments/formatting.md
  - gh-aw-fragments/rigor.md
engine:
  id: copilot
on:
  stale-check: false
  schedule:
    - cron: "0 6 * * 1"
  workflow_dispatch:
    inputs:
      title-prefix:
        description: "Title prefix for created issues"
        required: false
        default: "[oblt-aw][compiler-upgrade]"
  roles: [admin, maintainer, write]
  bots:
    - "github-actions[bot]"
concurrency:
  group: ${{ github.workflow }}-compiler-upgrade
  cancel-in-progress: true
permissions:
  copilot-requests: write
  contents: read
  issues: read
tools:
  github:
    toolsets: [repos, issues, search]
  bash: true
strict: false
safe-outputs:
  report-failed-jobs: false
  noop:
    report-as-issue: false
  create-issue:
    max: 1
    title-prefix: ${{ inputs.title-prefix }}
    close-older-key: "oblt-aw-compiler-upgrade"
    close-older-issues: true
    expires: 7d
timeout-minutes: 90
---

Check whether the pinned gh-aw compiler version in `.aw-compiler-version` is behind the latest upstream release.

### Data Gathering

1. Read `.aw-compiler-version` to get the pinned compiler version.
2. Read the repo's existing workflow sources to understand our current gh-aw usage and identify which compiler/frontmatter features we actually rely on.
3. Fetch recent gh-aw releases with `gh api repos/github/gh-aw/releases?per_page=10` and identify releases newer than the pinned version.
4. If the pinned version is already the latest release, call `noop` and stop.
5. For each newer release, read the release notes (`body`). If release notes are sparse, use the upstream changelog for confirmation.
6. If the release notes are broad or ambiguous, use a small multi-angle review: one pass for breaking changes, one for feature/value, and one for bug/security impact. Otherwise, do a single-pass review.
7. Compare the findings against our current workflow usage and decide whether the upgrade is actionable.

### What to Look For

Focus only on changes that affect workflow authors or this repository's current patterns:

1. **Breaking changes** — removed or renamed compiler/frontmatter/safe-output behavior, validation changes, or any note that requires workflow updates.
2. **New features worth adopting** — new compiler or workflow features that would benefit our current workflows.
3. **Bug fixes relevant to us** — fixes for issues we may be experiencing or workarounds we can remove.
4. **Security or hardening improvements** — anything that reduces risk in our current compiler or workflow setup.
5. **Compiler behavior changes** — new warnings, stricter validation, or changes in generated output that could affect compilation.

### What to Skip

- gh-aw internals that do not affect workflow authors.
- New features we do not use in this repository.
- Changelog entries already reflected in our current workflow configuration.

### How to Analyze

For each relevant release:

- cross-reference the release notes against the repository's current workflow files
- identify whether we use the affected feature or validation path
- classify the overall upgrade risk as **breaking**, **recommended**, or **informational**
- note the specific workflow files that would need updating if there is a breaking change
- prefer a single actionable issue over multiple near-duplicates

### Decision Rule

- If the pinned version is already current, call `noop`.
- If the newest release does not imply follow-up work for this repository, call `noop`.
- Otherwise, create one issue that summarizes the actionable upgrade and the required follow-up work.

### Issue Format

If and only if a newer version exists and there is actionable follow-up work, create a GitHub issue with:

- the current pinned version and latest upstream version
- a short risk assessment
- any breaking changes or required workflow updates, with affected files
- non-breaking fixes or features worth adopting
- a short implementation plan
- a note when the upgrade is only informational but still worth tracking

If no newer release exists, or if the new release does not imply follow-up work for this repository, call `noop`.

# Issue Fixer Routing

## Overview

Client template chain: `trigger-obs-aw-issue-comment.yml` → `obs-aw-event-issue-comment.yml` → `obs-aw-issue-fixer.yml`

Routed workflow:

- [.github/workflows/obs-aw-issue-fixer.yml](../../.github/workflows/obs-aw-issue-fixer.yml)

## Usage

Routing rules in `obs-aw-event-issue-comment.yml`:

- `issue_comment` + `created` +
  - `github.event.issue.pull_request == null` (comment is on an issue, not a PR)
  - `startsWith(github.event.comment.body, '/ai implement')`
  - `github.event.comment.author_association` is one of `OWNER`, `MEMBER`, or `COLLABORATOR`
  - issue title does **not** start with `[onboard]`
  - issue does **not** include `oblt-aw/onboard/repository`
  - issue does **not** include `oblt-aw/detector/security`
  - issue does **not** include `oblt-aw/detector/res-not-accessible-by-integration`
  - issue does **not** include any `oblt-aw/triage/security-*` label
  - issue does **not** include `oblt-aw/triage/res-not-accessible-by-integration`
  -> generic fixer

The exclusions ensure specialized fixers remain authoritative for security and resource-not-accessible-by-integration issues (including before specialized triage labels are applied), and keep repository-onboard issues for [`gh-aw-onboard-repository`](../workflows/gh-aw-onboard-repository.md). The event orchestrator also excludes `/ai implement` from the generic mention-in-issue route to avoid overlap.

## References

- [docs/workflows/obs-aw-issue-fixer.md](../workflows/obs-aw-issue-fixer.md)
- [docs/workflows/obs-aw-client-template.md](../workflows/obs-aw-client-template.md)

# Issue Fixer Routing

## Overview

Client template: `oblt-aw-issue-fixer.yml` → `oblt-aw-issue-fixer.yml`

Routed workflow:

- [.github/workflows/oblt-aw-issue-fixer.yml](../../.github/workflows/oblt-aw-issue-fixer.yml)

## Usage

Routing rules from ingress:

- `issue_comment` + `created` +
  - `github.event.issue.pull_request == null` (comment is on an issue, not a PR)
  - `startsWith(github.event.comment.body, '/ai implement')`
  - `github.event.comment.author_association` is one of `OWNER`, `MEMBER`, or `COLLABORATOR`
  - issue does **not** include any `oblt-aw/triage/security-*` label
  - issue does **not** include `oblt-aw/triage/res-not-accessible-by-integration`
  -> generic fixer

The exclusions ensure specialized fixers remain authoritative for security and resource-not-accessible-by-integration issues. Ingress also excludes `/ai implement` from the generic mention-in-issue route to avoid overlap.

## References

- [docs/workflows/oblt-aw-issue-fixer.md](../workflows/oblt-aw-issue-fixer.md)

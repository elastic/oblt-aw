# Issue Fixer Routing

## Overview

Entrypoint source: [.github/workflows/oblt-aw-ingress.yml](../../.github/workflows/oblt-aw-ingress.yml)

Routed workflow:

- [.github/workflows/gh-aw-issue-fixer.yml](../../.github/workflows/gh-aw-issue-fixer.yml)

## Usage

Routing rules from ingress:

- `issues` + `labeled` +
  - `github.event.label.name == 'oblt-aw/ai/fix-ready'`
  - issue does **not** include any `oblt-aw/triage/security-*` label
  - issue does **not** include `oblt-aw/triage/res-not-accessible-by-integration`
  -> generic fixer

The exclusions ensure specialized fixers remain authoritative for security and resource-not-accessible-by-integration issues.

## References

- [docs/workflows/gh-aw-issue-fixer.md](../workflows/gh-aw-issue-fixer.md)

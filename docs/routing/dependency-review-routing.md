# Dependency Review Routing

## Overview

Entrypoint source: [.github/workflows/oblt-aw-ingress.yml](../../.github/workflows/oblt-aw-ingress.yml)

Routed workflow source: [.github/workflows/gh-aw-dependency-review.yml](../../.github/workflows/gh-aw-dependency-review.yml)

## Usage

Ingress routes to dependency review when all conditions are true:

- `github.event_name == 'pull_request'`
- `github.event.action` is one of `opened`, `synchronize`, `reopened`
- `github.event.pull_request.user.login` is in:
  - `dependabot[bot]`
  - `renovate[bot]`
  - `Dependabot`
  - `Renovate`
  - `elastic-vault-github-plugin-prod[bot]`

## References

- [docs/workflows/gh-aw-dependency-review.md](../workflows/gh-aw-dependency-review.md)

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
- Dashboard gate passes for registry id `dependency-review` (`enabled-workflows` contains `obs:dependency-review` when `effective-raw` is non-empty).

For dashboard gate semantics (`get-enabled-workflows` and `enabled-workflows`), see [docs/workflows/oblt-aw-ingress.md](../workflows/oblt-aw-ingress.md).

## References

- [docs/workflows/gh-aw-dependency-review.md](../workflows/gh-aw-dependency-review.md)

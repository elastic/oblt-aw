# Dependency Review Routing

## Overview

Client template: `trigger-obs-aw-dependency-review.yml` → `obs-aw-dependency-review.yml`

Routed workflow source: [.github/workflows/obs-aw-dependency-review.yml](../../.github/workflows/obs-aw-dependency-review.yml)

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
- Dashboard gate passes for registry id `dependency-review` (`enabled-workflows` contains `obs:dependency-review`).

For dashboard gate semantics (`get-enabled-workflows` and `enabled-workflows`), see [docs/workflows/aw-prelude.md](../workflows/aw-prelude.md).

## References

- [docs/workflows/obs-aw-dependency-review.md](../workflows/obs-aw-dependency-review.md)

# Dependency Review Routing

## Overview

Client template chain: `trigger-obs-aw-pull-request.yml` → `obs-aw-event-pull-request.yml` → `obs-aw-dependency-review.yml`

Routed workflow source: [.github/workflows/obs-aw-dependency-review.yml](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/obs-aw-dependency-review.yml)

## Usage

`obs-aw-event-pull-request.yml` routes to dependency review when all conditions are true:

- `github.event_name == 'pull_request'`
- `github.event.action` is one of `opened`, `synchronize`, `reopened`
- `github.event.pull_request.user.login` is in:
  - `dependabot[bot]`
  - `renovate[bot]`
  - `Dependabot`
  - `Renovate`
  - `elastic-renovate-prod[bot]`
  - `elastic-vault-github-plugin-prod[bot]`
  - `github-actions[bot]`
- Control Plane dashboard gate passes for registry id `dependency-review` (`enabled-workflows` contains `obs:dependency-review`).

For Control Plane dashboard gate semantics (`get-enabled-workflows` and `enabled-workflows`), see [docs/workflows/aw-prelude.md](../workflows/aw-prelude.md).

When the lock succeeds without a `comment_id`, `notify-no-comment` upserts a single comment on the triggering PR (marker `obs-aw-dependency-review:notify-no-comment`; run URL + retry guidance). See [docs/workflows/obs-aw-dependency-review.md](../workflows/obs-aw-dependency-review.md) for the empty-safe-outputs failure mode.

The agentic lock lives in-repo as `gh-aw-dependency-review` (Observability-owned). Bots and the `oblt-aw/ai/merge-ready` allowlist are hardcoded on that source. The merge-ready **risk ceiling** comes from consumer APM (`workflows.dependency-review.policy.max-merge-ready-risk`; default `low-to-moderate`), resolved at the PR **base** SHA via `consumer-ref` (not the PR head). The wrapper also forwards `shared-proceed`, `shared-token-policy`, and resolved consumer instructions (including the Effective Dependency Review Policy block).

## References

- User guide: [Get Dependency Review on pull requests](../user-guide/dependency-review.md)
- [docs/workflows/obs-aw-dependency-review.md](../workflows/obs-aw-dependency-review.md)
- [docs/workflows/obs-aw-client-template.md](../workflows/obs-aw-client-template.md)
- Live E2E: [docs/testing/dependency-review-e2e.md](../testing/dependency-review-e2e.md)

# Dependency review routing

This folder documents routing and conventions for dependency update PR analysis.

## Entrypoint route

`oblt-aw-ingress.yml` dispatches to `gh-aw-dependency-review.yml` when:

- event is `pull_request`
- action is one of `opened`, `synchronize`, `reopened`
- PR author is one of: `dependabot[bot]`, `renovate[bot]`, `Dependabot`, `Renovate`, `elastic-vault-github-plugin-prod[bot]`

## Behavior extensions

The dependency review workflow adds repository-specific instructions to:

- include CVE-focused changelog/internal-change analysis
- apply label `oblt-aw/ai/merge-ready` when the review concludes with no risk, no breaking changes, and passing ecosystem checks

# Resource not accessible by integration

This folder groups routing/configuration guidance for the reusable workflows in this domain.

## Entry point

Use `.github/workflows/oblt-aw-ingress.yml` as the only reusable workflow reference from target repositories.

## Repository filters

Repository filters are defined in each specialized reusable workflow via `workflow_call` input `target-repositories`.

Behavior:

- `[]` means allow all repositories.
- non-empty list means only repositories included in that list are allowed.
- repository values use `{owner}/{repo}` format.

## Routed workflows

- schedule / workflow_dispatch -> `gh-aw-resource-not-accessible-by-integration-detector.yml`
- issues opened -> `gh-aw-resource-not-accessible-by-integration-triage.yml`
- issues labeled with `oblt-aw/ai/fix-ready` and `oblt-aw/triage/resource-not-accessible-by-integration` -> `gh-aw-resource-not-accessible-by-integration-fixer.yml`

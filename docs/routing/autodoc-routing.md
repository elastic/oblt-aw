# Autodoc Routing

## Overview

Client template: `trigger-obs-aw-schedule.yml` → `obs-aw-event-schedule.yml` → `obs-aw-autodoc.yml`

Routed workflow source: `.github/workflows/obs-aw-autodoc.yml`

## Usage

Ingress routes to autodoc when:

- `github.event_name` is `schedule` or `workflow_dispatch` on the schedule client trigger
- The Control Plane dashboard gate allows registry id `autodoc` (see `docs/workflows/aw-prelude.md` — `get-enabled-workflows` / `enabled-workflows`)

The event name is evaluated in the context of the workflow run that invoked the ingress (`workflow_call`).

## Routed workflow

- `schedule` / `workflow_dispatch` → `obs-aw-autodoc.yml`

## Notes

- `obs-aw-autodoc.yml` audit stage uses the Observability-owned lock in this repository:
  - `elastic/oblt-aw/.github/workflows/gh-aw-docs-patrol.lock.yml@main` — detects documentation drift and creates an issue with findings (source: [`.github/workflows/gh-aw-docs-patrol.md`](../../.github/workflows/gh-aw-docs-patrol.md))
- Fix stage still uses upstream `elastic/ai-github-actions/.../gh-aw-create-pr-from-issue.lock.yml@main` until that primitive is migrated ([#2053](https://github.com/elastic/oblt-aw/issues/2053)).
- It is intended to analyze repository documentation and open a focused documentation PR.
- It must not merge PRs automatically.

### Cutover / rollback (audit)

**Cutover:** audit `uses` the in-repo docs-patrol lock (`@main`).

**Rollback:** point audit back at `elastic/ai-github-actions/.github/workflows/gh-aw-docs-patrol.lock.yml@main` with the prior `with:` inputs (`lookback-window`, `title-prefix`, `additional-instructions`, `report-failure-as-issue: false`). See [obs-aw-autodoc.md](../workflows/obs-aw-autodoc.md).

## References

- `docs/workflows/obs-aw-autodoc.md`
- E2E: `docs/testing/autodoc-e2e.md`

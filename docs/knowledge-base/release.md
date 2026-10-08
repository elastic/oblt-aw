---
navigation_title: Release
description: How oblt-aw promotes and rolls back framework pins for consumers.
applies_to: {}
---

# Release

How framework changes move from `main` to production consumer pins, and how to roll back.

## Flow

1. Merge to `main` after PR CI (unit, functional, integration — not live E2E).
2. Manually dispatch [`aw-release-promote.yml`](../workflows/aw-release-promote.md) on the default branch with `release-type` (`patch` / `minor` / `major`).
3. Promote calls `e2e-all` on the tip SHA at dispatch, then tags, lands `config/release-pointers.json`, and creates a GitHub Release.
4. Distribute rewrites production installs to `tags.current` (for example `@v0`). Development repos stay on `@main`.

Rollback is a separate manual dispatch: [`aw-release-rollback.yml`](../workflows/aw-release-rollback.md) (confirm input must be `rollback`).

## Pins at a glance

| Class | Pin | Who |
|-------|-----|-----|
| `development` | Always `@main` | Pilot / early-detection repos, including `elastic/oblt-aw` |
| `production` | `tags.current` after promote | Everyone else in the active lists |

Template source under `.github/remote-workflow-template/` stays `@main`. Distribute substitutes the install pin from each repo’s `pin-class`.

## Docs

| Topic | Doc |
|-------|-----|
| Full model and runbook | [Release model](../operations/release-model.md) |
| Promote workflow | [aw-release-promote](../workflows/aw-release-promote.md) |
| Rollback workflow | [aw-release-rollback](../workflows/aw-release-rollback.md) |
| Testing contract (E2E gate) | [QA](qa/index.md) |
| Distribution | [distribute-client-workflow](../operations/distribute-client-workflow.md) |

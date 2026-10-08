---
navigation_title: E2E
description: Live end-to-end harnesses and promote gating for oblt-aw agentic routes.
applies_to: {}
---

# E2E

Proves the production-like path: client/orchestrator routing, prelude gate, resolve assets, agent job, and observable side effects under a controlled consumer environment (`elastic/oblt-aw` for current slices).

Not part of default PR `python-tests`. Runs on promote and via manual dispatch.

## Where it runs

| Trigger | Workflow | Role |
|---------|----------|------|
| Promote | `aw-release-promote.yml` → `e2e-all.yml` | Mandatory gate before tags / pointers |
| Smoke / health | `e2e-all.yml` or leaf `workflow_dispatch` | No tagging; `checkout-ref` defaults to `main` |

Promote pins harness checkout to `github.sha` (tip of `main` at dispatch). See [Release](../release.md).

## Oracles

Prefer stronger, cheaper checks first — job path success, structured side effects (comment/issue markers), schemas. Do not assert bit-identical LLM free text.

Quarantined or missing required cases **block** production promote (fail-closed).

## Harness docs

| Route | Doc |
|-------|-----|
| Autodoc | [autodoc-e2e](../../testing/autodoc-e2e.md) |
| Automerge VM images | [automerge-vm-images-e2e](../../testing/automerge-vm-images-e2e.md) |
| Dependency review | [dependency-review-e2e](../../testing/dependency-review-e2e.md) |
| ESTC PR Buildkite Detective | [estc-pr-buildkite-detective-e2e](../../testing/estc-pr-buildkite-detective-e2e.md) |
| PR Actions Detective | [pr-actions-detective-e2e](../../testing/pr-actions-detective-e2e.md) |
| Index | [Testing](../../testing/index.md) |

## See also

- Design: [Testing platform](../../architecture/agentic-workflow-testing-platform.md)
- [QA overview](index.md)
- [Release model](../../operations/release-model.md)

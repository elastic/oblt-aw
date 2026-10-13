---
navigation_title: QA
description: Testing layers for oblt-aw — unit, integration, and E2E — and how they gate merge and promote.
applies_to: {}
---

# QA

`oblt-aw` combines deterministic framework logic with stochastic agent runs. The testing platform covers that surface in layers: lower layers run on every PR; live E2E gates promote, not merge.

Design authority: [Agentic workflow testing platform](../../architecture/agentic-workflow-testing-platform.md).

```mermaid
flowchart TB
  U[Unit]
  I[Integration]
  E[E2E]
  U --> I --> E
  E --> R[Release promote]
```

## Layers

| Layer | What it proves | When it runs |
|-------|----------------|--------------|
| [Unit](unit.md) | Pure logic and contracts | Every PR |
| [Integration](integration.md) | Wrapper ↔ lock ↔ policy wiring without a live model | Every PR |
| [E2E](e2e.md) | Production-like agent path and observable side effects | Manual / promote (`e2e-all`) |

Functional checks (workflow validators, pre-commit, actionlint) sit alongside unit and integration on every PR. See [ci.yml](../../workflows/ci.md).

## Related

- [Release](../release.md) — promote consumes E2E as a mandatory gate
- Live harness notes: [Testing](../../testing/index.md)

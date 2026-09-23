# Dependency Review — fixtures and E2E cases

Assets for `obs:dependency-review` at the **integration** and **E2E** layers
(see [agentic-workflow-testing-platform](../../../docs/architecture/agentic-workflow-testing-platform.md)).

## Integration (`consumer/` / `expected/`)

| Path | Role |
|------|------|
| `consumer/` | Synthetic consumer repo root (`apm.yml` + optional AI fragments) |
| `expected/` | Deterministic expectations for resolve outputs (no live model) |

Exercised by `tests/integration/test_dependency_review.py`.

## E2E cases (`cases/`)

| Case id | Mode | Purpose |
|---------|------|---------|
| `actions-pin-bump-live` | live (E2E) | Vault Actions pin-bump PR → DR comment + merge-ready |

See [docs/testing/dependency-review-e2e.md](../../../docs/testing/dependency-review-e2e.md).

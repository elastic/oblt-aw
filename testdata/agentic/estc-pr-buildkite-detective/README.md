# ESTC PR Buildkite Detective — fixtures and E2E cases

Assets for `obs:estc-pr-buildkite-detective` at the **integration** and **E2E** layers
(see [agentic-workflow-testing-platform](../../../docs/architecture/agentic-workflow-testing-platform.md)).

## Integration (`consumer/` / `expected/`)

| Path | Role |
|------|------|
| `consumer/` | Synthetic consumer repo root (`apm.yml` + optional AI fragments) |
| `expected/` | Deterministic expectations for resolve outputs (no live model) |

Exercised by `tests/integration/test_estc_pr_buildkite_detective.py` via
`pytest tests/` (no GitHub agent run, no token minting).

**Deferred:** token-policy dry-run / mocked `create-token` for this slice
(open question on [#1910](https://github.com/elastic/oblt-aw/issues/1910)).

## E2E cases (`cases/`)

```text
testdata/agentic/estc-pr-buildkite-detective/
  cases/<case-id>/
    case.json                 # live expectations + trigger contract
```

| Case id | Mode | Purpose |
|---------|------|---------|
| `status-failure-open-pr-live` | live (E2E) | Production status→agent→PR comment |
| `status-success-skipped` | live (E2E) | Success status must not run detective |
| `status-failure-non-buildkite` | live (E2E) | Non-Buildkite failure must not run detective |
| `status-failure-no-open-pr` | live (E2E) | Failed Buildkite status without open PR stops before agent |

## Notes

- Live cases drive the real `trigger-obs-aw-status.yml` path on `elastic/oblt-aw`.
- Integration wiring is separate from E2E cases — see `consumer/` / `expected/` and [#1910](https://github.com/elastic/oblt-aw/issues/1910).
- See [docs/testing/estc-pr-buildkite-detective-e2e.md](../../../docs/testing/estc-pr-buildkite-detective-e2e.md).

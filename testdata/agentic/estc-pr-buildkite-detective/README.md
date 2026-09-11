# Fixtures: `estc-pr-buildkite-detective` integration

Frozen consumer-side assets for the first vertical-slice **integration** layer
(see [agentic-workflow-testing-platform](../../../docs/architecture/agentic-workflow-testing-platform.md)).

| Path | Role |
|------|------|
| `consumer/` | Synthetic consumer repo root (`apm.yml` + optional AI fragments) |
| `expected/` | Deterministic expectations for resolve outputs (no live model) |

Exercised by `tests/integration/test_estc_pr_buildkite_detective.py` via
`pytest tests/` (no GitHub agent run, no token minting).

**Deferred:** token-policy dry-run / mocked `create-token` for this slice
(open question on [#1910](https://github.com/elastic/oblt-aw/issues/1910)).

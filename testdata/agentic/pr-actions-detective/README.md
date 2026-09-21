# PR Actions Detective — integration fixtures

Assets for `obs:pr-actions-detective` at the **integration** layer
(see [agentic-workflow-testing-platform](../../../docs/architecture/agentic-workflow-testing-platform.md)).

## Integration (`consumer/` / `expected/`)

| Path | Role |
|------|------|
| `consumer/` | Synthetic consumer repo root (`apm.yml` + optional AI fragments) |
| `expected/` | Deterministic expectations for resolve outputs (no live model) |

Exercised by `tests/integration/test_pr_actions_detective.py` via
`pytest tests/integration` (no GitHub agent run, no token minting).

## Notes

- Live E2E for Actions `workflow_run` failures is out of scope for [#2055](https://github.com/elastic/oblt-aw/issues/2055).
- Integration wiring mirrors the estc detective pattern; this wrapper has no
  `platform-additional-instructions` on the resolve job.

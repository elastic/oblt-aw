# PR Actions Detective — integration and E2E fixtures

Assets for `obs:pr-actions-detective` (see [agentic-workflow-testing-platform](../../../docs/architecture/agentic-workflow-testing-platform.md)).

## Integration (`consumer/` / `expected/`)

| Path | Role |
|------|------|
| `consumer/` | Synthetic consumer repo root (`apm.yml` + optional AI fragments) |
| `expected/` | Deterministic expectations for resolve outputs (no live model) |

Exercised by `tests/integration/test_pr_actions_detective.py` via
`pytest tests/integration` (no GitHub agent run, no token minting).

## Live E2E (`cases/`)

| Path | Role |
|------|------|
| `cases/workflow-run-failure-open-pr-live/` | Live happy path: intentional Actions failure → detective comment |
| `e2e-fixture-pr.md` | Marker kept on the long-lived fixture PR branch |
| `e2e-fail-trigger.md` | Path-filtered file the harness bumps each live run |

See [pr-actions-detective-e2e](../../../docs/testing/pr-actions-detective-e2e.md).

## Notes

- Integration wiring mirrors the estc detective pattern; this wrapper has no
  `platform-additional-instructions` on the resolve job.
- Live E2E mirrors the estc status harness, substituting a GitHub Actions fail
  workflow for Buildkite.

# E2E harness: `obs:repo-scheduled`

Production end-to-end harness for consumer-defined scheduled automations ([#2197](https://github.com/elastic/oblt-aw/issues/2197)). Mirrors the autodoc schedule live pattern.

## What this harness covers

Live E2E only against **`elastic/oblt-aw`**:

1. Enablement gate for `obs:repo-scheduled` on the Control Plane dashboard.
2. Verify the **checked-in** bait instruction at [`.github/ai/scheduled/e2e-repo-scheduled-bait.md`](../../.github/ai/scheduled/e2e-repo-scheduled-bait.md) on the default branch. No Contents create/delete on `main`.
3. Snapshot existing E2E schedule-trigger run IDs, then dispatch `e2e-trigger-obs-aw-schedule.yml` with `e2e-repo-scheduled-mode=true` (and `e2e-autodoc-mode=false`) → prelude → `obs-aw-repo-scheduled` agent. Production `trigger-obs-aw-schedule-*.yml` clients are not used.
4. Wait for a **new** nested **run-automation / agent** leaf success (matrix id `e2e-repo-scheduled-bait`) and an open issue titled with `[oblt-aw][repo-scheduled]` whose body cites the bait path and `E2E_REPO_SCHEDULED_BAIT_MARKER`.
5. Cleanup: close only that issue. The bait instruction remains on the default branch; record `bait_present` after cleanup (exact content match).

Oracle pass/fail for agent side effects is **issue presence** (number + URL) plus `cleanup.completed` **and** `cleanup.bait_present` when `cleanup_after` / `seed_instruction_bait` are true. Issue body prose beyond bait path / marker correlation is out of scope.

## Live cases

| Case id | Expectation |
|---------|-------------|
| `schedule-issue-live` | Verify bait → schedule dispatch with E2E mode → agent → issue with `[oblt-aw][repo-scheduled]` prefix |

## Prerequisites (live)

1. **Control Plane dashboard** — enable `obs:repo-scheduled` for `elastic/oblt-aw`.
2. **Bait fixture** — `.github/ai/scheduled/e2e-repo-scheduled-bait.md` must be present on the default branch (merged via normal PR).
3. **Permissions** — the E2E workflow needs Actions write (dispatch schedule) and Issues write (close cleanup).
4. **Collateral** — dispatching the schedule trigger may also run other dashboard-enabled daily routes. The harness polls only for the repo-scheduled agent leaf and sets autodoc E2E mode off.
5. **Duration** — budget up to ~2 hours for the agent path.

## How to run

### GitHub Actions (preferred)

```bash
gh workflow run e2e-repo-scheduled.yml
```

To run every leaf E2E: `gh workflow run e2e-all.yml`.

Triggers: `workflow_dispatch` and `workflow_call` (from `e2e-all.yml`). Concurrency group `e2e-repo-scheduled`.

### Harness/oracle unit coverage (no live agent)

```bash
pytest tests/e2e/test_repo_scheduled_e2e.py -v
```

## Artifacts

Each run uploads `e2e-repo-scheduled-<case_id>-<run_id>` with `outcome.json`, `oracle-report.json`, and `summary.json`.

## Related

- Config: [`config/obs/e2e-repo-scheduled.json`](https://github.com/elastic/oblt-aw/blob/main/config/obs/e2e-repo-scheduled.json)
- Harness/oracle: [`scripts/obs/e2e/`](https://github.com/elastic/oblt-aw/tree/main/scripts/obs/e2e)
- Workflow doc: [obs-aw-repo-scheduled](../workflows/obs-aw-repo-scheduled.md)
- Design: [agentic-workflow-testing-platform](../architecture/agentic-workflow-testing-platform.md)

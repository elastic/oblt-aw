# E2E harness: `obs:repo-scheduled`

Production end-to-end harness for consumer-defined scheduled automations ([#2197](https://github.com/elastic/oblt-aw/issues/2197)). Mirrors the autodoc schedule live pattern.

## What this harness covers

Live E2E only against **`elastic/oblt-aw`**:

1. Enablement gate for `obs:repo-scheduled` on the Control Plane dashboard.
2. Verify the **checked-in** bait instruction at [`.github/ai/scheduled/e2e-repo-scheduled-bait.md`](../../.github/ai/scheduled/e2e-repo-scheduled-bait.md) on the default branch. No Contents create/delete on `main`. No permanent root `apm.yml` on the control plane (same idea as automerge-all-files keeping policy under `testdata/`).
3. When `e2e-repo-scheduled-mode=true`, discovery **injects** that bait file if `apm.yml` does not list it (`--e2e-bait-only`). Preflight runs that resolve step before dispatch.
4. Snapshot existing E2E schedule-trigger run IDs, then dispatch `e2e-trigger-obs-aw-schedule.yml` (and `e2e-autodoc-mode=false`) → prelude → `obs-aw-repo-scheduled`. Production `trigger-obs-aw-schedule-*.yml` clients are not used.
5. Wait for the correlated schedule-trigger run to complete. If the case requires the bait agent leaf and the run finishes without it, the harness **fails closed immediately** (does not poll until the 2h timeout). For `schedule-noop-live`, success requires named `discover-automations` success and no bait agent leaf — not merely any completed correlated run.
6. Issue case: wait for an open issue titled with `[oblt-aw][repo-scheduled]` whose body cites the bait path and `E2E_REPO_SCHEDULED_BAIT_MARKER`, then close that issue on cleanup. The bait file stays on the default branch.

Oracle pass/fail for agent side effects is **issue presence** (number + URL) plus `cleanup.completed` **and** `cleanup.bait_present` when `cleanup_after` / `seed_instruction_bait` are true. Issue body prose beyond bait path / marker correlation is out of scope.

## Live cases

| Case id | Expectation |
|---------|-------------|
| `schedule-issue-live` | E2E mode → inject bait → agent leaf → issue with `[oblt-aw][repo-scheduled]` prefix |
| `schedule-noop-live` | Normal wake (E2E mode off, no control-plane apm automations) → successful empty discover → no bait agent leaf → no bait issue |

## Prerequisites (live)

1. **Control Plane dashboard** — enable `obs:repo-scheduled` for `elastic/oblt-aw`.
2. **Bait fixture** — `.github/ai/scheduled/e2e-repo-scheduled-bait.md` must be present on the default branch (merged via normal PR).
3. **Permissions** — the E2E workflow needs Actions write (dispatch schedule) and Issues write (close cleanup).
4. **Collateral** — under `e2e-all.yml`, repo-scheduled runs **after** autodoc so the shared schedule trigger is not dispatched in parallel. Prefer `gh workflow run e2e-repo-scheduled.yml` for an isolated smoke.
5. **Duration** — budget agent time for the issue case; failed discovers/agent skips should surface in minutes, not hours.

## How to run

### GitHub Actions (preferred)

```bash
gh workflow run e2e-repo-scheduled.yml
```

To run every leaf E2E: `gh workflow run e2e-all.yml`.

Triggers: `workflow_dispatch` and `workflow_call` (from `e2e-all.yml`). Concurrency group `e2e-repo-scheduled`.

### Harness/oracle unit coverage (no live agent)

```bash
pytest tests/e2e/test_repo_scheduled_e2e.py tests/unit/test_repo_scheduled_instructions.py -v
```

## Artifacts

Each run uploads `e2e-repo-scheduled-<case_id>-<run_id>` with `outcome.json`, `oracle-report.json`, and `summary.json`.

## Related

- Config: [`config/obs/e2e-repo-scheduled.json`](https://github.com/elastic/oblt-aw/blob/main/config/obs/e2e-repo-scheduled.json)
- Example consumer APM fragment (fixture only): [`testdata/agentic/repo-scheduled/policy-apm.yml`](../../testdata/agentic/repo-scheduled/policy-apm.yml)
- Harness/oracle: [`scripts/obs/e2e/`](https://github.com/elastic/oblt-aw/tree/main/scripts/obs/e2e)
- Workflow doc: [obs-aw-repo-scheduled](../workflows/obs-aw-repo-scheduled.md)
- Design: [agentic-workflow-testing-platform](../architecture/agentic-workflow-testing-platform.md)

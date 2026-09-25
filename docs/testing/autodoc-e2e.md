# E2E harness: `obs:autodoc`

Production end-to-end harness for the autodoc **audit** and **fix** stages ([#2052](https://github.com/elastic/oblt-aw/issues/2052), [#2053](https://github.com/elastic/oblt-aw/issues/2053)). Mirrors the ESTC / automerge live pattern.

## What this harness covers

Live E2E only against **`elastic/oblt-aw`**:

1. Enablement gate for `obs:autodoc` on the Control Plane Dashboard.
2. Verify the **checked-in** intentional undocumented bait at [`scripts/e2e_autodoc_intentional_undocumented.py`](../../scripts/e2e_autodoc_intentional_undocumented.py) on the default branch (see [autodoc-e2e-bait](autodoc-e2e-bait.md)). No Contents create/delete on `main`.
3. Snapshot existing schedule-trigger run IDs, then dispatch `trigger-obs-aw-schedule.yml` with `e2e-additional-instructions` that force docs-patrol to evaluate the bait path and embed a per-run `E2E_AUTODOC_RUN_TOKEN=…` in the issue body → prelude → `obs-aw-autodoc` audit (`gh-aw-docs-patrol`).
4. Wait for a **new** nested **audit** agent leaf job success (not a pre-existing concurrent run, and not fix/sibling agent jobs) and an open issue titled with `[oblt-aw][autodoc]` whose body cites the bait path and the per-run token marker.
5. For the fix-path case: wait for nested **fix** / create-PR agent success and an open PR that references that issue (title `docs: Documentation analysis and improvement`).
6. Cleanup: close only that issue and close only PRs that reference it. The bait fixture remains on the default branch; record `bait_present` after cleanup.

Oracle pass/fail for agent side effects is **issue / PR presence** (number + URL) plus `cleanup.completed` **and** `cleanup.bait_present` when `cleanup_after` / `seed_doc_drift_bait` are true. Issue or PR body prose beyond bait path / run-token correlation is out of scope.

## Live cases

| Case id | Expectation |
|---------|-------------|
| `schedule-audit-issue-live` | Verify bait → schedule dispatch with E2E instructions → audit agent → issue with `[oblt-aw][autodoc]` prefix |
| `schedule-audit-fix-pr-live` | Same as above, then fix agent → PR linked to that issue |

The GitHub Actions workflow runs **`schedule-audit-fix-pr-live`** (full path). The audit-only case remains for oracle unit coverage and optional local harness runs.

## Prerequisites (live)

1. **Dashboard** — enable `obs:autodoc` on the Control Plane Dashboard for `elastic/oblt-aw`.
2. **Bait fixture** — `scripts/e2e_autodoc_intentional_undocumented.py` must be present on the default branch (merged via normal PR).
3. **Permissions** — the E2E workflow needs Actions write (dispatch schedule), Issues write (close cleanup), and Pull requests write (close fix PRs).
4. **Collateral** — dispatching the schedule trigger may also run other dashboard-enabled schedule routes (agent-suggestions, security detectors). The harness polls only for autodoc audit / fix agent leaf jobs.
5. **Duration** — the fix path runs a second Copilot stage; budget up to ~3 hours.

Control-plane lock/wrapper still resolve via `@main` on the live schedule path (smoke); candidate-ref pinning is a separate follow-up.

## How to run

### GitHub Actions (preferred)

```bash
gh workflow run e2e-autodoc.yml
```

To run every leaf E2E: `gh workflow run e2e-all.yml`.

Triggers: `workflow_dispatch` and `workflow_call` (from `e2e-all.yml`). Concurrency group `e2e-autodoc`.

### Harness/oracle unit coverage (no live agent)

```bash
pytest tests/e2e/test_autodoc_e2e.py -v
```

## Artifacts

Each run uploads `e2e-autodoc-<case_id>-<run_id>` with `outcome.json`, `oracle-report.json`, and `summary.json`.

## Related

- Bait fixture: [autodoc-e2e-bait](autodoc-e2e-bait.md)
- Config: [`config/obs/e2e-autodoc.json`](../../config/obs/e2e-autodoc.json)
- Harness/oracle: [`scripts/obs/e2e/`](../../scripts/obs/e2e/)
- Workflow doc: [obs-aw-autodoc](../workflows/obs-aw-autodoc.md)
- Design: [agentic-workflow-testing-platform](../architecture/agentic-workflow-testing-platform.md)

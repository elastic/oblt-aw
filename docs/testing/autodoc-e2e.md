# E2E harness: `obs:autodoc`

Production end-to-end harness for the autodoc **audit** stage ([#2052](https://github.com/elastic/oblt-aw/issues/2052)). Mirrors the ESTC / automerge live pattern.

## What this harness covers

Live E2E only against **`elastic/oblt-aw`**:

1. Enablement gate for `obs:autodoc` on the Control Plane Dashboard.
2. Seed intentional undocumented public API bait on the default branch (within the docs-patrol lookback window).
3. Dispatch `trigger-obs-aw-schedule.yml` → prelude → `obs-aw-autodoc` audit (`gh-aw-docs-patrol`).
4. Wait for the nested audit agent job success and an open issue titled with `[oblt-aw][autodoc]`.
5. Cleanup: close the issue, close any autodoc fix PR opened in the window, delete the bait file.

Oracle pass/fail for the agent side effect is **issue presence** (number + URL). Issue body prose is out of scope.

## Live case

| Case id | Expectation |
|---------|-------------|
| `schedule-audit-issue-live` | Seed bait → schedule dispatch → audit agent → issue with `[oblt-aw][autodoc]` prefix |

## Prerequisites (live)

1. **Dashboard** — enable `obs:autodoc` on the Control Plane Dashboard for `elastic/oblt-aw`.
2. **Permissions** — the E2E workflow needs Contents write (bait), Actions write (dispatch schedule), Issues write (close cleanup), Pull requests write (close fix PRs).
3. **Collateral** — dispatching the schedule trigger may also run other dashboard-enabled schedule routes (agent-suggestions, security detectors). The harness polls only for the autodoc audit agent leaf job.

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

Each run uploads `e2e-autodoc-schedule-audit-issue-live-<run_id>` with `outcome.json`, `oracle-report.json`, and `summary.json`.

## Related

- Config: [`config/obs/e2e-autodoc.json`](../../config/obs/e2e-autodoc.json)
- Harness/oracle: [`scripts/obs/e2e/`](../../scripts/obs/e2e/)
- Workflow doc: [obs-aw-autodoc](../workflows/obs-aw-autodoc.md)
- Design: [agentic-workflow-testing-platform](../architecture/agentic-workflow-testing-platform.md)

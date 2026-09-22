# E2E harness: `obs:pr-actions-detective`

Production end-to-end harness for the PR Actions Detective route ([#2055](https://github.com/elastic/oblt-aw/issues/2055) follow-on; testing platform [#1877](https://github.com/elastic/oblt-aw/issues/1877)). Design authority: [agentic-workflow-testing-platform](../architecture/agentic-workflow-testing-platform.md). Pattern sibling: [estc-pr-buildkite-detective-e2e](estc-pr-buildkite-detective-e2e.md).

## What this harness covers

Live E2E only: intentional failed GitHub Actions run → `workflow_run` → `trigger-obs-aw-workflow-run.yml` → prelude → wrapper → lock → agent on **`elastic/oblt-aw`**.

Integration wiring (resolve → wrapper → lock inputs, no live model) lives under `tests/integration/` and `testdata/.../consumer/` / `expected/` ([#2055](https://github.com/elastic/oblt-aw/issues/2055)).

## Live case

| Case id | Expectation |
|---------|-------------|
| `workflow-run-failure-open-pr-live` | Sync intentional fail workflow + bump trigger file on the fixture PR → fail workflow concludes `failure` → agent posts a comment (harness finds it via `### TL;DR` + `## Remediation`; oracle asserts presence only) |

Oracle pass/fail for the agent side effect is **comment presence**. Section markers are **identity** for find/clear in the harness; asserting marker shape in the oracle is deferred. Agent prose content is out of scope.

## Prerequisites (live)

1. **Dashboard** — enable `obs:pr-actions-detective` on the Control Plane Dashboard for `elastic/oblt-aw` (issue labeled `oblt-aw/dashboard`). The harness fails closed if the checkbox is off (`dashboard_enabled` is pinned true).
2. **Vault app token** — the leaf workflow mints an ephemeral token via `elastic/oblt-actions/github/create-token` using `workflow-token-policy` from [`config/e2e.json`](../../config/e2e.json) (same shared E2E policy as automerge). Fixture Contents commits and PR writes must not use `github.token` — `GITHUB_TOKEN` commits do not reliably fire `pull_request`, and github-actions[bot] authorship can hit the approval gate.
3. **Client trigger** — `trigger-obs-aw-workflow-run.yml` must be installed on `elastic/oblt-aw` (distributed via the obs client template).
4. **Target PR** — harness creates or reuses one **long-lived** fixture PR labeled `e2e:pr-actions-detective` on branch `e2e/pr-actions-detective`. It is never closed by the harness. The `ci-gate` job in `ci.yml` skips work jobs for any `e2e:*` / `e2e/` fixture; the exact Actions-detective label/branch also skips agentic pull-request routes so the fixture does not burn CI or agent credits. Workflow concurrency (`e2e-pr-actions-detective`) serializes live runs against that shared fixture.
5. **Fail workflow** — [`.github/workflows/e2e-pr-actions-detective-fail.yml`](../../.github/workflows/e2e-pr-actions-detective-fail.yml) runs only on the fixture PR (label + branch + same-repo). Each live run **seeds** that YAML onto the fixture tip when missing, no-ops when it already matches the checkout, and **refuses** to overwrite a differing remote copy (update the fixture via a normal PR). Only [`testdata/agentic/pr-actions-detective/e2e-fail-trigger.md`](../../testdata/agentic/pr-actions-detective/e2e-fail-trigger.md) is intentionally mutated each run so `pull_request` synchronize fires a real failed run (required so `workflow_run.pull_requests` is non-empty).

### Reading failures

Harness and oracle print `block_reason` / failed checks in the job log (and emit `::error::` annotations). Artifacts still include `outcome.json`, `oracle-report.json`, and `summary.json` (`failure_detail`, `failed_checks`).

## How to run

### GitHub Actions (preferred)

Workflow: [`.github/workflows/e2e-pr-actions-detective.yml`](../../.github/workflows/e2e-pr-actions-detective.yml)

```bash
gh workflow run e2e-pr-actions-detective.yml
```

To run every leaf E2E (this one plus others): `gh workflow run e2e-all.yml`.

Triggers:

- `workflow_dispatch` (manual) and `workflow_call` (from `e2e-all.yml`). One run at a time via concurrency group `e2e-pr-actions-detective`. Always runs case `workflow-run-failure-open-pr-live`.

Not part of the default PR `required` job in [`ci.yml`](../../.github/workflows/ci.yml). Control-plane lock/wrapper still resolve via `@main` on the live path (smoke); candidate-ref pinning is a separate follow-up.

### Local (live only)

Live mode needs `gh` auth and dashboard enablement.

Harness/oracle unit coverage (no live agent):

```bash
pytest tests/e2e/test_pr_actions_detective_e2e.py -v
```

## Artifacts

Each run uploads `e2e-pr-actions-detective-workflow-run-failure-open-pr-live-<run_id>` containing:

| File | Purpose |
|------|---------|
| `outcome.json` | Harness structured outcome |
| `oracle-report.json` | Per-check pass/fail details |
| `summary.json` | Compact `{pass, run_url, workflow_id, layer, mode, case_id, agent_invoked, …}` |

## Related

- Config: [`config/obs/e2e-pr-actions-detective.json`](../../config/obs/e2e-pr-actions-detective.json)
- Harness/oracle: [`scripts/obs/e2e/`](../../scripts/obs/e2e/)
- Workflow doc: [obs-aw-pr-actions-detective](../workflows/obs-aw-pr-actions-detective.md)
- Design: [agentic-workflow-testing-platform](../architecture/agentic-workflow-testing-platform.md)
- Integration fixtures (sibling): [#2055](https://github.com/elastic/oblt-aw/issues/2055)

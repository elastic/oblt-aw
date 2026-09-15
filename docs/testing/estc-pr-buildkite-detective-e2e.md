# E2E harness: `obs:estc-pr-buildkite-detective`

Production end-to-end harness for the PR Buildkite Detective route ([#1911](https://github.com/elastic/oblt-aw/issues/1911)). Design authority: [agentic-workflow-testing-platform](../architecture/agentic-workflow-testing-platform.md).

## What this harness covers

Live E2E only: real Buildkite failure → Buildkite-published `status` → `trigger-obs-aw-status.yml` → prelude → wrapper → lock → agent on **`elastic/oblt-aw`**.

Integration wiring (resolve → wrapper → lock inputs, no live model) lives under `tests/integration/` and `testdata/.../consumer/` / `expected/` ([#1910](https://github.com/elastic/oblt-aw/issues/1910)).

## Live case

| Case id | Expectation |
|---------|-------------|
| `status-failure-open-pr-live` | Create intentional Buildkite failure → **Buildkite** publishes failed status → agent posts a comment (harness finds it via `### TL;DR` + `## Remediation`; oracle asserts presence only) |

Oracle pass/fail for the agent side effect is **comment presence**. Section markers are **identity** for find/clear in the harness; asserting marker shape in the oracle is deferred to a follow-up. Agent prose / commit diagnosis content is out of scope.

## Prerequisites (live)

1. **Dashboard** — enable `obs:estc-pr-buildkite-detective` on the Control Plane Dashboard for `elastic/oblt-aw` (issue labeled `oblt-aw/dashboard`). Currently required; the harness fails closed if the checkbox is off.
2. **Secret** — `BUILDKITE_LOGS_API_TOKEN` on `elastic/oblt-aw` (mapped by `trigger-obs-aw-status.yml` into the wrapper). Must be able to **read** the E2E fail pipeline’s builds/logs.
3. **Secret** — `BUILDKITE_TOKEN` with Buildkite scopes **`write_builds`** (+ read) / pipeline access level that can create builds so the harness can create and poll an intentional failure build.
4. **Buildkite pipeline** — provisioned via [`catalog-info.yaml`](../../catalog-info.yaml) Resource `buildkite-pipeline-oblt-aw-e2e-estc-fail` (steps: [`.buildkite/pipeline.e2e-estc-fail.yml`](../../.buildkite/pipeline.e2e-estc-fail.yml) with **pipeline-level** `notify: github_commit_status` only, Beats-style context `oblt-aw-e2e-estc-fail: buildkite`). After merge to `main`, confirm RRE reconciliation at https://buildkite.com/elastic/oblt-aw-e2e-estc-fail (`publish_commit_status: false` — statuses come from notify; reserved `buildkite/…` contexts are rejected when live `prevent_custom_statuses_from_using_buildkite_prefix` is true). See [`.buildkite/README.e2e-estc-fail.md`](../../.buildkite/README.e2e-estc-fail.md). Optional vars: `E2E_BUILDKITE_ORG` (default `elastic`), `E2E_BUILDKITE_PIPELINE` (default `oblt-aw-e2e-estc-fail`) — notify context must match E2E `status_context` / harness expectation.
5. **Target PR** — harness always finds or creates an open PR labeled `e2e:estc-pr-buildkite-detective` on branch `e2e/estc-pr-buildkite-detective` (reopens that fixture if it was closed). The development PR that starts a path-filtered run is **not** the Buildkite target. That **exact** label (plus the fixture branch/repo guards in workflow `if` conditions) skips repo `ci.yml` and agentic pull-request routes (`obs-aw-dependency-review`, `obs-aw-automerge`) so this fixture PR does not burn CI or agent credits.

### Reading failures

Harness and oracle print `block_reason` / failed checks in the job log (and emit `::error::` annotations). Artifacts still include `outcome.json`, `oracle-report.json`, and `summary.json` (`failure_detail`, `failed_checks`).

## How to run

### GitHub Actions (preferred)

Workflow: [`.github/workflows/e2e-estc-pr-buildkite-detective.yml`](../../.github/workflows/e2e-estc-pr-buildkite-detective.yml)

```bash
# Full live matrix (happy path only) — uses the fixture PR
gh workflow run e2e-estc-pr-buildkite-detective.yml \
  -f case-id=all

# Explicit happy-path case
gh workflow run e2e-estc-pr-buildkite-detective.yml \
  -f case-id=status-failure-open-pr-live
```

Triggers:

- `pull_request` (`opened` / `synchronize` / `reopened`) when ESTC detective–related paths change — same-repo only; still uses the fixture PR as the Buildkite target
- `workflow_dispatch` (manual) — fixture PR
- `workflow_call` for the release/promote train ([#1878](https://github.com/elastic/oblt-aw/issues/1878)) — consume `outputs.pass` and uploaded `summary.json`

Not part of the default PR `required` job in [`ci.yml`](../../.github/workflows/ci.yml). Control-plane lock/wrapper still resolve via `@main` on the live status path (smoke); candidate-ref pinning is a separate follow-up.

### Local (live only)

Live mode needs `gh` auth, dashboard enablement, `BUILDKITE_TOKEN`, and the intentional-failure Buildkite pipeline.

Harness/oracle unit coverage (no live agent):

```bash
pytest tests/e2e/test_estc_pr_buildkite_detective_e2e.py -v
```

## Artifacts (promote contract for #1878)

Each matrix leg uploads `e2e-estc-pr-buildkite-detective-<case-id>-<run_id>` containing:

| File | Purpose |
|------|---------|
| `outcome.json` | Harness structured outcome |
| `oracle-report.json` | Per-check pass/fail details |
| `summary.json` | Compact `{pass, run_url, workflow_id, layer, mode, case_id, agent_invoked, …}` |

Promote should read `summary.pass` — not agent free text. Quarantined cases set `pass: false` (and `quarantined: true`) so `outputs.pass` fails closed for promote (#1878). The reusable workflow exposes `outputs.pass` from the aggregate gate job.

## Quarantine policy

Config: [`config/obs/e2e-quarantine.json`](../../config/obs/e2e-quarantine.json)

- Every quarantine entry **must** include `owner` and `reason` (invalid rows are ignored, not treated as skip-pass).
- Quarantined cases are reported as skipped **and** `pass: false` so they block the E2E gate / promote — **not** silently retried into green.

## Related

- Config: [`config/obs/e2e-estc-pr-buildkite-detective.json`](../../config/obs/e2e-estc-pr-buildkite-detective.json)
- Workflow doc: [obs-aw-estc-pr-buildkite-detective](../workflows/obs-aw-estc-pr-buildkite-detective.md)
- Design: [agentic-workflow-testing-platform](../architecture/agentic-workflow-testing-platform.md)
- Integration fixtures (sibling): [#1910](https://github.com/elastic/oblt-aw/issues/1910)
- Promote consumer: [#1878](https://github.com/elastic/oblt-aw/issues/1878)

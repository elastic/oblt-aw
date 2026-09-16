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
3. **Secret** — `E2E_GH_TOKEN` when exercising negative live cases that need the harness-posted status path. `github.token` cannot trigger that workflow path, so the harness uses this secret to post the status that drives the negative case.
4. **Secret** — `BUILDKITE_TOKEN` with Buildkite scopes **`write_builds`** (+ read) / pipeline access level that can create builds so the harness can create and poll an intentional failure build.
5. **Buildkite pipeline** — provisioned via [`catalog-info.yaml`](../../catalog-info.yaml) Resource `buildkite-pipeline-oblt-aw-e2e-estc-fail` (steps: [`.buildkite/pipeline.e2e-estc-fail.yml`](../../.buildkite/pipeline.e2e-estc-fail.yml); statuses from `publish_commit_status: true`, context `buildkite/<pipeline>` e.g. `buildkite/oblt-aw-e2e-estc-fail`). After merge to `main`, confirm RRE reconciliation at https://buildkite.com/elastic/oblt-aw-e2e-estc-fail. See [`.buildkite/README.e2e-estc-fail.md`](../../.buildkite/README.e2e-estc-fail.md). Optional vars: `E2E_BUILDKITE_ORG` (default `elastic`), `E2E_BUILDKITE_PIPELINE` (default `oblt-aw-e2e-estc-fail`) — the harness derives the expected status context from the resolved pipeline name only.
6. **Target PR** — harness creates or reuses one **long-lived** fixture PR labeled `e2e:estc-pr-buildkite-detective` on branch `e2e/estc-pr-buildkite-detective`. It is never closed by the harness. The exact label plus fixture branch skips repo `ci.yml` and agentic pull-request routes so the fixture does not burn CI or agent credits. Workflow concurrency (`e2e-estc-pr-buildkite-detective`) serializes live runs against that shared fixture. After syncing the fail-pipeline YAML onto the fixture branch, the harness creates the Buildkite build on the **Contents PUT commit SHA** (not a re-fetched PR `headRefOid`, which can lag and hide the status from the PR Checks UI).
7. **Status context** — waiter always expects `buildkite/<resolved pipeline>` (from `E2E_BUILDKITE_PIPELINE` / config defaults). Config overrides that disagree fail closed before create.

### Reading failures

Harness and oracle print `block_reason` / failed checks in the job log (and emit `::error::` annotations). Artifacts still include `outcome.json`, `oracle-report.json`, and `summary.json` (`failure_detail`, `failed_checks`).

## How to run

### GitHub Actions (preferred)

Workflow: [`.github/workflows/e2e-estc-pr-buildkite-detective.yml`](../../.github/workflows/e2e-estc-pr-buildkite-detective.yml)

```bash
gh workflow run e2e-estc-pr-buildkite-detective.yml
```

Triggers:

- `workflow_dispatch` only (manual). One run at a time via concurrency group `e2e-estc-pr-buildkite-detective`. Always runs case `status-failure-open-pr-live`.

Not part of the default PR `required` job in [`ci.yml`](../../.github/workflows/ci.yml). Control-plane lock/wrapper still resolve via `@main` on the live status path (smoke); candidate-ref pinning is a separate follow-up.

### Local (live only)

Live mode needs `gh` auth, dashboard enablement, `BUILDKITE_TOKEN`, `E2E_GH_TOKEN` for negative cases that post statuses, and the intentional-failure Buildkite pipeline.

Harness/oracle unit coverage (no live agent):

```bash
pytest tests/e2e/test_estc_pr_buildkite_detective_e2e.py -v
```

## Artifacts

Each run uploads `e2e-estc-pr-buildkite-detective-status-failure-open-pr-live-<run_id>` containing:

| File | Purpose |
|------|---------|
| `outcome.json` | Harness structured outcome |
| `oracle-report.json` | Per-check pass/fail details |
| `summary.json` | Compact `{pass, run_url, workflow_id, layer, mode, case_id, agent_invoked, …}` |

## Related

- Config: [`config/obs/e2e-estc-pr-buildkite-detective.json`](../../config/obs/e2e-estc-pr-buildkite-detective.json)
- Workflow doc: [obs-aw-estc-pr-buildkite-detective](../workflows/obs-aw-estc-pr-buildkite-detective.md)
- Design: [agentic-workflow-testing-platform](../architecture/agentic-workflow-testing-platform.md)
- Integration fixtures (sibling): [#1910](https://github.com/elastic/oblt-aw/issues/1910)

# E2E harness: `obs:estc-pr-buildkite-detective`

Production end-to-end harness for the PR Buildkite Detective route ([#1911](https://github.com/elastic/oblt-aw/issues/1911)). Design authority: [agentic-workflow-testing-platform](../architecture/agentic-workflow-testing-platform.md).

## What this harness covers

| Mode | What runs | Live agent? | When |
|------|-----------|-------------|------|
| **live** | Real `status` → `trigger-obs-aw-status.yml` → prelude → wrapper → lock → agent on **`elastic/oblt-aw`** | Yes | Default for `workflow_dispatch`, weekly schedule, and `workflow_call` (release/#1878) |
| **fixture** | Recorded status/Buildkite gates only (integration layer) | No | Optional dispatch (`mode=fixture`) |

Live mode is the E2E proof. On the happy path the intentional Buildkite pipeline publishes the GitHub status (real event). Fixture mode is a cheaper integration check of pre-agent gates.

## Live cases

| Case id | Expectation |
|---------|-------------|
| `status-failure-open-pr-live` | Create intentional Buildkite failure → **Buildkite** publishes failed status → agent posts a comment (harness finds it via `### TL;DR` + `## Remediation`; oracle asserts presence only) |
| `status-success-skipped` | Success status → status job skipped → no agent comment |
| `status-failure-non-buildkite` | Failed non-Buildkite status → status job skipped → no agent comment |
| `status-failure-no-open-pr` | Failed Buildkite status on default-branch HEAD with no open PR → status job runs, agent does not comment |

Oracle pass/fail for the agent side effect is **comment presence or absence**. Section markers are **identity** for find/clear in the harness; asserting marker shape in the oracle is deferred to a follow-up. Agent prose / commit diagnosis content is out of scope.

## Prerequisites (live)

1. **Dashboard** — enable `obs:estc-pr-buildkite-detective` on the Control Plane Dashboard for `elastic/oblt-aw` (issue labeled `oblt-aw/dashboard`). Currently required; the harness fails closed if the checkbox is off.
2. **Secret** — `BUILDKITE_LOGS_API_TOKEN` on `elastic/oblt-aw` (mapped by `trigger-obs-aw-status.yml` into the wrapper). Must be able to **read** the E2E fail pipeline’s builds/logs.
3. **Secret** — `BUILDKITE_TOKEN` with Buildkite scopes **`write_builds`** (+ read) so the harness can create and poll an intentional failure build.
4. **Buildkite pipeline** — provisioned via [`catalog-info.yaml`](../../catalog-info.yaml) Resource `buildkite-pipeline-oblt-aw-e2e-estc-fail` (steps: [`.buildkite/pipeline.e2e-estc-fail.yml`](../../.buildkite/pipeline.e2e-estc-fail.yml)). After merge to `main`, confirm RRE reconciliation at https://buildkite.com/elastic/oblt-aw-e2e-estc-fail. See [`.buildkite/README.e2e-estc-fail.md`](../../.buildkite/README.e2e-estc-fail.md). Optional vars: `E2E_BUILDKITE_ORG` (default `elastic`), `E2E_BUILDKITE_PIPELINE` (default `oblt-aw-e2e-estc-fail`).
5. **E2E PR** — harness finds or creates an open PR labeled `e2e:estc-pr-buildkite-detective` on branch `e2e/estc-pr-buildkite-detective`. That **exact** label (plus the fixture branch/repo guards in workflow `if` conditions) skips repo `ci.yml` and agentic pull-request routes (`obs-aw-dependency-review`, `obs-aw-automerge`) so this fixture PR does not burn CI or agent credits.
6. **Optional override** — Actions var `E2E_ESTC_BUILDKITE_TARGET_URL` skips create and reuses a fixed failed build URL (escape hatch only).

## How to run

### GitHub Actions (preferred)

Workflow: [`.github/workflows/e2e-estc-pr-buildkite-detective.yml`](../../.github/workflows/e2e-estc-pr-buildkite-detective.yml)

```bash
# Full live matrix
gh workflow run e2e-estc-pr-buildkite-detective.yml \
  -f mode=live \
  -f case-id=all

# Single live case
gh workflow run e2e-estc-pr-buildkite-detective.yml \
  -f mode=live \
  -f case-id=status-failure-open-pr-live
```

Triggers:

- `workflow_dispatch` (manual)
- Weekly schedule (`17 6 * * 1`, live matrix)
- `workflow_call` for the release/promote train ([#1878](https://github.com/elastic/oblt-aw/issues/1878)) — consume `outputs.pass` and uploaded `summary.json`

Not part of the default PR `required` job in [`ci.yml`](../../.github/workflows/ci.yml).

### Local (fixture / integration only)

```bash
mkdir -p /tmp/estc-e2e
python3 scripts/estc_pr_buildkite_detective_e2e_harness.py \
  --mode fixture \
  --case-id status-failure-open-pr \
  --outcome-path /tmp/estc-e2e/outcome.json

python3 scripts/oracle_estc_pr_buildkite_detective_e2e.py \
  --outcome-path /tmp/estc-e2e/outcome.json \
  --report-path /tmp/estc-e2e/oracle-report.json \
  --summary-path /tmp/estc-e2e/summary.json \
  --quarantine-path config/obs/e2e-quarantine.json
```

Live mode needs `gh` auth, dashboard enablement, `BUILDKITE_TOKEN`, and the intentional-failure Buildkite pipeline (or the optional URL override).

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

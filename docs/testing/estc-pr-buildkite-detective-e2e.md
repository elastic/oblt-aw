# E2E harness: `obs:estc-pr-buildkite-detective`

First vertical-slice end-to-end harness for the PR Buildkite Detective route ([#1911](https://github.com/elastic/oblt-aw/issues/1911)). Design authority: [agentic-workflow-testing-platform](../architecture/agentic-workflow-testing-platform.md).

## What this harness covers (v1)

| Mode | What runs | Live agent? | Default |
|------|-----------|-------------|---------|
| **fixture** | Status-failure gates + recorded Buildkite resolution + structured oracle | No | Yes (`workflow_dispatch` default and weekly schedule) |
| **live** | Reserved for a sandbox consumer run of the real status → wrapper → lock path | Would require sandbox + secrets | Dispatch-only; **blocked** until sandbox Unknowns are resolved |

Fixture mode intentionally stops before the paid GH-AW agent. It still exercises the production path filters (failed Buildkite `status`, open PR association, Buildkite URL parse, failed job collection) against recorded payloads.

## How to run

### Local

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

### GitHub Actions

Workflow: [`.github/workflows/aw-e2e-estc-pr-buildkite-detective.yml`](../../.github/workflows/aw-e2e-estc-pr-buildkite-detective.yml)

```bash
gh workflow run aw-e2e-estc-pr-buildkite-detective.yml \
  -f mode=fixture \
  -f case-id=status-failure-open-pr
```

This workflow is **not** part of the default PR `required` job in [`ci.yml`](../../.github/workflows/ci.yml).

## Artifacts (promote contract for #1878)

Each run uploads `e2e-estc-pr-buildkite-detective-<run_id>` containing:

| File | Purpose |
|------|---------|
| `outcome.json` | Harness structured outcome (gates + Buildkite markers) |
| `oracle-report.json` | Per-check pass/fail details |
| `summary.json` | Compact `{pass, run_url, workflow_id, layer, mode, case_id, …}` for promote |

Promote should read `summary.pass` (and quarantine/skipped flags) — not agent free text.

## Sandbox inventory (Unknowns)

Searched active Observability consumers and org sandbox naming. No dedicated Observability agentic-workflow sandbox repository exists today (`elastic/oblt-aw-sandbox` and `elastic/obs-aw-sandbox` were not found). Docs team has `elastic/docs-actions-sandbox` (private) as a precedent, not an Observability consumer.

| Item | Status | Notes |
|------|--------|-------|
| Sandbox repository | **Unknown** | **Recommended name:** `elastic/oblt-aw-sandbox`. Place under Observability ownership; register later in `config/obs/active-repositories.json` only when intentionally distributing client triggers. |
| Dashboard enablement | **Unknown** | Once the sandbox exists: sync Control Plane Dashboard, enable `obs:estc-pr-buildkite-detective`. |
| Client triggers installed | **Unknown** | Need `trigger-obs-aw-status.yml` (or equivalent) in the sandbox for live status replay. |
| Open PR + failed Buildkite status | **Unknown** | Live mode needs a controllable failing check context containing `buildkite`. |

### Checklist to un-block live mode

1. Create `elastic/oblt-aw-sandbox` (or chosen name) with a maintainable fixture PR branch.
2. Add repository secrets / org secret access for `BUILDKITE_LOGS_API_TOKEN` (consumer mapping → wrapper `BUILDKITE_API_TOKEN`).
3. Create/verify token policies in `elastic/catalog-info` if prelude/`create-token` is required; record exact `workflow-token-policy` / `ai-assets-token-policy` names (currently **Unknown** for the future sandbox row).
4. Install client status trigger; enable dashboard checkbox for `obs:estc-pr-buildkite-detective`.
5. Wire live mode in the E2E workflow to dispatch/replay a controlled status failure (still prefer recorded Buildkite payloads inside the agent step when possible).

## Secrets and token-policy inventory

| Secret / policy | Where used | v1 fixture | Live (future) |
|-----------------|------------|------------|---------------|
| `BUILDKITE_LOGS_API_TOKEN` → `BUILDKITE_API_TOKEN` | Client `trigger-obs-aw-status.yml` → `obs-aw-event-status` → wrapper/lock | Not required (fixtures) | **Required** — Unknown whether org or repo secret will back the sandbox |
| `GITHUB_TOKEN` / ephemeral create-token | Prelude, resolve assets, PR comment side effects | Not required for fixture harness | **Required** — exact `workflow-token-policy` for sandbox **Unknown** |
| `ai-assets-token-policy` | `aw-resolve-agentic-assets` when consumer configures it | N/A | **Unknown** (empty string vs named policy) |
| Copilot / model credentials | GH-AW lock agent job | **Must not** run on every PR; fixture mode avoids this | **Unknown** cost/quotas for scheduled live runs |

Do not invent credential values or claim a policy name exists without catalog verification.

## Quarantine policy

Config: [`config/obs/e2e-quarantine.json`](../../config/obs/e2e-quarantine.json)

- Default owner team: `@elastic/observablt-robots`
- Add an entry with `workflow_id`, `case_id`, `owner`, and `reason` to skip a flaky case
- Quarantined cases are reported as skipped — **not** silently retried into green
- Example entry:

```json
{
  "workflow_id": "obs:estc-pr-buildkite-detective",
  "case_id": "status-failure-open-pr",
  "owner": "@elastic/observablt-robots",
  "reason": "Intermittent fixture parse until #NNNN",
  "added": "2026-09-11"
}
```

## Fixtures

See [`testdata/agentic/estc-pr-buildkite-detective/`](../../testdata/agentic/estc-pr-buildkite-detective/).

## Related

- Workflow doc: [obs-aw-estc-pr-buildkite-detective](../workflows/obs-aw-estc-pr-buildkite-detective.md)
- Design: [agentic-workflow-testing-platform](../architecture/agentic-workflow-testing-platform.md)
- Integration fixtures (sibling): [#1910](https://github.com/elastic/oblt-aw/issues/1910)
- Promote consumer: [#1878](https://github.com/elastic/oblt-aw/issues/1878)

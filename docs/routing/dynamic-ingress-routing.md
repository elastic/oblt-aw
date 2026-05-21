# Dynamic ingress routing

Ingress no longer declares one top-level job per `gh-aw-*` workflow with event-type `if:` gating (which produced many **skipped** checks on pull requests). Instead:

1. **`plan-routes`** — [`scripts/plan_ingress_routes.py`](../../scripts/plan_ingress_routes.py) evaluates dashboard, authors, labels, and event context and writes route outputs to `GITHUB_OUTPUT`.
2. **[`oblt-aw-ingress.yml`](../../.github/workflows/oblt-aw-ingress.yml)** (after `plan-routes`):
   - **`publish-planned-dispatch`** — [`scripts/generate_planned_dispatch.py`](../../scripts/generate_planned_dispatch.py) generates the planned dispatch workflow; ingress checks out **`elastic/oblt-aw`** with an ephemeral token from [`elastic/oblt-actions/github/create-token@v1`](https://github.com/elastic/oblt-actions/tree/v1/github/create-token) (auto role from the caller workflow ref), prepares `DISPATCH_BRANCH`, commits when the file changed, and pushes the dispatch branch (with rebase retry on rejection). Each generated job has a literal `uses: elastic/oblt-aw/.github/workflows/gh-aw-*.yml@<control-plane-ref>`.
   - **`invoke-planned-dispatch`** — literal `uses: …/DISPATCH_WORKFLOW@DISPATCH_BRANCH` (must match the ingress `env` block; expressions are not allowed in `uses:`).

No matrix, no per-route invoke wrappers, no manifest layer.

## Why one generated file on a fixed branch?

GitHub Actions does not allow expressions in reusable `uses:` (path or `@ref`). The workaround is to **generate** one YAML file with only the jobs needed for this event, each with **literal** `uses:` lines (from [`config/obs/workflow-registry.json`](../../config/obs/workflow-registry.json) via [`scripts/generate_planned_dispatch.py`](../../scripts/generate_planned_dispatch.py)), commit it on the dispatch branch in **`elastic/oblt-aw`** (ingress checks out that repo from the caller workflow; fetch and check out the branch when it already exists, otherwise create it), push without force, then call it with a **fixed** `uses: …@oblt-aw/dispatch/working`.

## Adding or changing a route

1. Register the workflow in [`config/obs/workflow-registry.json`](../../config/obs/workflow-registry.json) with dashboard metadata (`id`, `name`, `description`, `maturity`, `default_enabled`).
2. Add a **`dispatch`** list on that entry. Each item needs `id` (ingress route id), `workflow` (gh-aw filename), and `secrets`; optional `with_input`: `allowed-pr` or `allowed-issue`. Use one item for simple workflows; multiple items for features like `security` (detector/fixer/triage).
3. Add gating in [`scripts/plan_ingress_routes.py`](../../scripts/plan_ingress_routes.py) (`ROUTE_EVALUATORS` + evaluator).
4. Add tests in [`tests/test_plan_ingress_routes.py`](../../tests/test_plan_ingress_routes.py) and [`tests/test_generate_planned_dispatch.py`](../../tests/test_generate_planned_dispatch.py).

## PR check noise

A typical `pull_request` run previously showed ~15 skipped ingress jobs. After planning, only jobs for eligible routes appear under `invoke-planned-dispatch` (often 0–2).

## Local validation

```bash
python -c "from generate_planned_dispatch import load_route_specs, render_planned_dispatch_workflow; load_route_specs(); print(render_planned_dispatch_workflow(['automerge'], 'main'))"
python scripts/generate_planned_dispatch.py \
  --routes-json '["automerge"]' \
  --control-plane-ref main \
  --dispatch-workflow oblt-aw-planned-dispatch.yml \
  --output /tmp/oblt-aw-planned-dispatch.yml
pytest tests/test_plan_ingress_routes.py tests/test_generate_planned_dispatch.py
```

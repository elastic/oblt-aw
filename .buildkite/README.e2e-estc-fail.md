# Buildkite pipeline: E2E intentional failure

Used by the live harness for [`obs:estc-pr-buildkite-detective`](../docs/testing/estc-pr-buildkite-detective-e2e.md).

## One-time setup

1. In Buildkite org (default `elastic`, override with Actions var `E2E_BUILDKITE_ORG`), create pipeline slug `oblt-aw-e2e-estc-fail` (or `E2E_BUILDKITE_PIPELINE`).
2. Repository: `elastic/oblt-aw`.
3. Steps: YAML from [pipeline.e2e-estc-fail.yml](pipeline.e2e-estc-fail.yml) (pipeline settings → steps from repository, or paste).
4. Assign a cluster/queue that can run a trivial shell step.
5. Add repo secret `E2E_BUILDKITE_API_TOKEN` with scopes **`write_builds`** and read access to this pipeline (create + poll). The detective path still uses `BUILDKITE_LOGS_API_TOKEN` for log fetch during the agent job — that token must also be able to **read** this pipeline’s builds/logs.

## Runtime

The E2E harness creates a build on the long-lived E2E PR branch/SHA (with `pull_request_id`), waits until `failed`, then posts a GitHub commit status whose `target_url` is that build’s `web_url`.

Optional escape hatch: set Actions var `E2E_ESTC_BUILDKITE_TARGET_URL` to skip create and reuse a fixed URL.

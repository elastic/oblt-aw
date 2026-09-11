# Buildkite pipeline: E2E intentional failure

Used by the live harness for [`obs:estc-pr-buildkite-detective`](../docs/testing/estc-pr-buildkite-detective-e2e.md).

## Provisioning

The pipeline is declared in [`catalog-info.yaml`](../catalog-info.yaml) as Resource `buildkite-pipeline-oblt-aw-e2e-estc-fail` (`implementation.metadata.name: oblt-aw-e2e-estc-fail`, `pipeline_file: .buildkite/pipeline.e2e-estc-fail.yml`, `provider_settings.trigger_mode: none` so only the API creates builds).

After merge to `main`, wait for the Buildkite RRE to reconcile. Confirm the pipeline exists at https://buildkite.com/elastic/oblt-aw-e2e-estc-fail.

## Secrets (still required)

1. Repo secret `E2E_BUILDKITE_API_TOKEN` with Buildkite scopes **`write_builds`** (+ read) so the harness can create and poll builds.
2. Repo secret `BUILDKITE_LOGS_API_TOKEN` (mapped into the detective) must be able to **read** this pipeline’s builds/logs.

Optional vars: `E2E_BUILDKITE_ORG` (default `elastic`), `E2E_BUILDKITE_PIPELINE` (default `oblt-aw-e2e-estc-fail`).

## Runtime

Happy path:

1. Harness creates a Buildkite build on the long-lived E2E PR branch/SHA (with `pull_request_id`).
2. The intentional-failure step runs and fails.
3. **Buildkite** publishes the GitHub commit status (`publish_commit_status: true`) with `target_url` pointing at that build.
4. The real `status` event triggers `trigger-obs-aw-status.yml` → detective → agent.
5. Harness observes the Actions run and PR comment (it does **not** forge the happy-path status).

Gate cases (success / non-Buildkite / no-open-PR) still use harness-posted synthetic statuses.

Optional escape hatch: set Actions var `E2E_ESTC_BUILDKITE_TARGET_URL` to skip create; the harness then posts the status itself using that URL.

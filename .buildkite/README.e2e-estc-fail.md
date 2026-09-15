# Buildkite pipeline: E2E intentional failure

Used by the live harness for [`obs:estc-pr-buildkite-detective`](../docs/testing/estc-pr-buildkite-detective-e2e.md).

## Provisioning

The pipeline is declared in [`catalog-info.yaml`](../catalog-info.yaml) as Resource `buildkite-pipeline-oblt-aw-e2e-estc-fail` (`implementation.metadata.name: oblt-aw-e2e-estc-fail`, `pipeline_file: .buildkite/pipeline.e2e-estc-fail.yml`, `provider_settings.trigger_mode: none` so only the API creates builds).

After merge to `main`, wait for the Buildkite RRE to reconcile. Confirm the pipeline exists at https://buildkite.com/elastic/oblt-aw-e2e-estc-fail.

## Secrets (still required)

1. Repo secret `BUILDKITE_TOKEN` with Buildkite scopes **`write_builds`** (+ read) so the harness can create and poll builds.
2. Repo secret `BUILDKITE_LOGS_API_TOKEN` (mapped into the detective) must be able to **read** this pipeline’s builds/logs.

Optional vars: `E2E_BUILDKITE_ORG` (default `elastic`), `E2E_BUILDKITE_PIPELINE` (default `oblt-aw-e2e-estc-fail`).

## Runtime

Happy path:

1. Harness creates a Buildkite build on the long-lived E2E PR branch/SHA (with `pull_request_id`).
2. Before create, the harness syncs [`.buildkite/pipeline.e2e-estc-fail.yml`](pipeline.e2e-estc-fail.yml) onto that fixture branch so the build’s checkout includes the current notify block. Sync and Buildkite publish preflight are skipped when `E2E_ESTC_BUILDKITE_TARGET_URL` is set.
3. The intentional-failure step runs and fails.
4. **Buildkite** publishes the GitHub commit status for context `buildkite/elastic/oblt-aw-e2e-estc-fail` via **pipeline-level** `notify: github_commit_status` only (and `publish_commit_status: true` in [`catalog-info.yaml`](../catalog-info.yaml)). Do not add `prevent_custom_statuses_from_using_buildkite_prefix` to the catalog RRE — Terrazzo rejects that key. The harness fails closed only if the live Buildkite API reports that setting as `true`. Do not add the same context at step scope — that can double-trigger the detective.
5. The real `status` event triggers `trigger-obs-aw-status.yml` → detective → agent.
6. Harness observes the Actions run and PR comment (it does **not** forge the happy-path status).

If the status never appears: check Buildkite GitHub App (`buildkite-limited-access`) commit-status permission, pipeline GitHub settings, and the harness job log (`block_reason` + status dump). Do not paper over a missing Buildkite status by forging one on the happy path.

Gate cases (success / non-Buildkite / no-open-PR) still use harness-posted synthetic statuses.

Optional escape hatch: set Actions var `E2E_ESTC_BUILDKITE_TARGET_URL` to skip create; the harness then posts the status itself using that URL (no fixture-branch sync, no Buildkite publish preflight).

If you override `E2E_BUILDKITE_ORG` / `E2E_BUILDKITE_PIPELINE`, the fail-pipeline notify context must still match `buildkite/<org>/<pipeline>` (or set `expected_status_context`); otherwise the harness blocks before create.

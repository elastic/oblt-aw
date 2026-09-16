# Buildkite pipeline: E2E intentional failure

Used by the live harness for [`obs:estc-pr-buildkite-detective`](../docs/testing/estc-pr-buildkite-detective-e2e.md).

## Provisioning

The pipeline is declared in [`catalog-info.yaml`](../catalog-info.yaml) as Resource `buildkite-pipeline-oblt-aw-e2e-estc-fail` (`implementation.metadata.name: oblt-aw-e2e-estc-fail`, `pipeline_file: .buildkite/pipeline.e2e-estc-fail.yml`, `provider_settings.trigger_mode: code` so GitHub commit statuses can update, with `build_branches` / `build_pull_requests` / `build_tags` false so only the API creates builds).

After merge to `main`, wait for the Buildkite RRE to reconcile. Confirm the pipeline exists at https://buildkite.com/elastic/oblt-aw-e2e-estc-fail and that `publish_commit_status` is enabled.

## Secrets (still required)

1. Repo secret `BUILDKITE_TOKEN` with Buildkite scopes **`write_builds`** (+ read) so the harness can create and poll builds.
2. Repo secret `BUILDKITE_LOGS_API_TOKEN` (mapped into the detective) must be able to **read** this pipeline’s builds/logs.

Optional vars: `E2E_BUILDKITE_ORG` (default `elastic`), `E2E_BUILDKITE_PIPELINE` (default `oblt-aw-e2e-estc-fail`).

## Runtime

Happy path:

1. Harness creates or reuses an **ephemeral** fixture PR/branch (`e2e/estc-pr-buildkite-detective/pr-<N>` for path-filtered runs, or `…/run-<id>` for dispatch/call), then creates a Buildkite build on that fixture SHA (with `pull_request_id`). After the matrix, cleanup closes the PR and deletes the branch; if cleanup fails, the next run reuses the same `pr-<N>` / `run-<id>` key.
2. The intentional-failure step runs and fails.
3. **Buildkite** publishes the GitHub commit status for context `buildkite/<pipeline>` (e.g. `buildkite/oblt-aw-e2e-estc-fail`) via catalog `publish_commit_status: true` (default Buildkite context). Do **not** add pipeline- or step-level `notify: github_commit_status` — that double-fires the detective.
4. The real `status` event triggers `trigger-obs-aw-status.yml` → detective → agent (context must contain substring `buildkite`). Pending statuses also fire the workflow but skip the job (`state != failure`); the harness ignores those skipped runs.
5. Harness observes the Actions run and PR comment (it does **not** forge the happy-path status).

When the harness syncs `.buildkite/pipeline.e2e-estc-fail.yml` onto the ephemeral fixture branch, it binds the Buildkite build (and status wait) to the **Contents API commit SHA** from that write. It must not re-read `headRefOid` from the PR API after sync — that OID can lag, leaving the status on a non-HEAD commit that does not appear in the PR Checks UI.

If the status never appears: check Buildkite GitHub App (`buildkite-limited-access`) commit-status permission, pipeline GitHub settings (`publish_commit_status`), and the harness job log (`block_reason` + status dump). Do not paper over a missing Buildkite status by forging one on the happy path.

Live E2E is happy-path only (no harness-posted synthetic statuses; no URL-override escape hatch).

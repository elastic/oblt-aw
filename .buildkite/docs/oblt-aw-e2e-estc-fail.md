-# Buildkite pipeline: `oblt-aw-e2e-estc-fail`
+# Buildkite pipeline: `oblt-aw-e2e-estc-fail`

## At a glance

| | |
| --- | --- |
| Platform | Buildkite |
| Source | [`pipeline.e2e-estc-fail.yml`](../pipeline.e2e-estc-fail.yml) |
| Trigger | The E2E harness creates a Buildkite build through the API; automatic branch, PR, and tag builds are disabled in the catalog resource |

## Purpose

Provides a deterministic failed Buildkite build for the live `obs:estc-pr-buildkite-detective` happy-path E2E. The stable log marker lets the harness and maintainers identify the intentional failure. It is not a product failure signal.

## Execution flow

The pipeline has one step, `intentional-e2e-failure`, which prints the marker and explanatory text, then exits with status 1. The source explicitly warns not to add step- or pipeline-level GitHub commit-status notifications because the catalog provider publishes the default Buildkite commit status.

The catalog resource names the pipeline `oblt-aw-e2e-estc-fail`, uses this file as its pipeline definition, enables code trigger mode and commit-status publishing, and disables automatic branch, pull-request, and tag builds. The E2E harness creates the build and waits for its real status.

## Inputs, outputs, and access

The checked-in YAML declares no inputs, secrets, plugins, or artifacts. Provisioning notes in [`README.e2e-estc-fail.md`](../README.e2e-estc-fail.md) list the Buildkite token and log-reading requirements for the GitHub harness/detective; secret values are intentionally not documented here.

## Operational notes

Keep the status publisher single-sourced through the catalog provider settings. The existing runbook also documents one-time pipeline setup, secret names, fixture lifecycle, and status troubleshooting; it is preserved as the operational reference.

## Sources

- [Fixture pipeline](../pipeline.e2e-estc-fail.yml)
- [Catalog resource](../../catalog-info.yaml)
- [Existing provisioning and runtime notes](../README.e2e-estc-fail.md)
- [GitHub E2E caller](../../.github/workflows/e2e-estc-pr-buildkite-detective.yml)
- [Status event route](../../docs/workflows/obs-aw-event-status.md)

# Workflow: `e2e-dependency-review-actions-fixture.yml`

## At a glance

| | |
| --- | --- |
| Platform | GitHub Actions |
| Source | [`.github/workflows/e2e-dependency-review-actions-fixture.yml`](../../.github/workflows/e2e-dependency-review-actions-fixture.yml) |
| Trigger | Pull requests changing this workflow file |

## Purpose

Provides the minimal same-repository Actions pin used by the live dependency-review E2E harness. The harness updates the pin on its ephemeral fixture pull request so the production dependency-review route processes a real change.

## Execution flow

For a pull request that changes only the path-filtered workflow file, the `fixture-checkout` job runs on `ubuntu-latest` and checks out the repository using a known full commit SHA. Other pull requests do not trigger this job.

## Inputs, outputs, and access

No inputs, outputs, or secrets are declared. The workflow and job request only `contents: read`.

## Sources

- [Fixture workflow](../../.github/workflows/e2e-dependency-review-actions-fixture.yml)
- [Dependency-review E2E](e2e-dependency-review.md)
- [Dependency-review route](obs-aw-dependency-review.md)

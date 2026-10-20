# Workflow: `e2e-all.yml`

## At a glance

| | |
| --- | --- |
| Platform | GitHub Actions |
| Source | [`.github/workflows/e2e-all.yml`](../../.github/workflows/e2e-all.yml) |
| Trigger | `workflow_dispatch` or `workflow_call` |

## Purpose

Orchestrates the checked-in live E2E workflows in parallel. The source says it is not a pull-request CI gate; release promotion calls it, and maintainers can dispatch it for smoke testing.

## When it runs

Both triggers accept optional `checkout-ref` (default `main`). A manual dispatch first checks out the repository default branch and validates that the requested ref is the default-branch tip or a full SHA on that branch's history. The workflow serializes runs with `cancel-in-progress: false`.

## Execution flow

After the dispatch validation succeeds (or is skipped for workflow calls), the workflow calls five leaf workflows: automerge VM images, dependency review, ESTC Buildkite detective, autodoc audit, and PR Actions detective. The leaves receive the same `checkout-ref` and inherited secrets. The calls can run independently after the validation job.

## Inputs, outputs, and access

`checkout-ref` is an optional string for both trigger types. No outputs are declared. Workflow permissions default to `contents: read`; leaf calls request write, Actions, status, check, and OIDC permissions as needed.

## Sources

- [Orchestrator](../../.github/workflows/e2e-all.yml)
- [Release promotion](aw-release-promote.md)
- [Checkout-ref validator](../../scripts/aw_e2e_validate_checkout_ref.py)
- [Automerge VM images E2E](e2e-automerge-vm-images.md)
- [Dependency review E2E](e2e-dependency-review.md)
- [ESTC Buildkite detective E2E](e2e-estc-pr-buildkite-detective.md)
- [Autodoc E2E](e2e-autodoc.md)
- [PR Actions detective E2E](e2e-pr-actions-detective.md)

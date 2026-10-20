# Workflow: `e2e-automerge-vm-images.yml`

## At a glance

| | |
| --- | --- |
| Platform | GitHub Actions |
| Source | [`.github/workflows/e2e-automerge-vm-images.yml`](../../.github/workflows/e2e-automerge-vm-images.yml) |
| Trigger | `workflow_dispatch` or `workflow_call` |

## Purpose

Exercises the live `obs:automerge:vm-images` route using an ephemeral updatecli-shaped image-pin pull request. The expected path is dependency review, merge-ready labeling, approval, and automerge. It is not a default PR CI gate.

## Execution flow

The `e2e` job validates a manual `checkout-ref`, resolves the Vault token policy from `config/e2e.json` for direct E2E dispatch or `config/release.json` when called from release promotion, then obtains an ephemeral Vault-app token. It installs Python 3.14 dependencies, runs `automerge_vm_images_e2e_harness.py`, and checks the structured result with `oracle_automerge_vm_images_e2e.py` against `testdata/agentic/automerge-vm-images`. Failure summaries and artifacts are retained for 30 days.

The job uses the `vm-images-bump-live` case ID, a 120-minute timeout, and non-cancelling concurrency. The workflow comments explain that the Vault app authors the fixture to avoid the GitHub Actions bot approval gate.

## Inputs, outputs, and access

Optional `checkout-ref` defaults to `main`. The job requests content and pull-request writes, Actions and checks reads, issue writes, and OIDC. No long-lived secret is declared; token-policy configuration is read from the checked-out JSON files.

## Sources

- [E2E workflow](../../.github/workflows/e2e-automerge-vm-images.yml)
- [Harness](../../scripts/obs/e2e/automerge_vm_images_e2e_harness.py)
- [Oracle](../../scripts/obs/e2e/oracle_automerge_vm_images_e2e.py)
- [Buildkite fixture pipeline](../../.buildkite/pipeline.e2e-automerge-vm-images.yml)
- [Automerge route](obs-aw-automerge.md)
- [Test fixtures](../../testdata/agentic/automerge-vm-images/)

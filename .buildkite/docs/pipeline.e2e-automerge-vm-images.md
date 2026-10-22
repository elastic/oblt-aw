-# Buildkite fixture pipeline: Automerge VM images E2E
+# Buildkite fixture pipeline: Automerge VM images E2E

## At a glance

| | |
| --- | --- |
| Platform | Buildkite |
| Source | [`pipeline.e2e-automerge-vm-images.yml`](../pipeline.e2e-automerge-vm-images.yml) |
| Trigger | No Buildkite trigger is declared in the checked-in YAML; the GitHub E2E harness manages the fixture |

## Purpose

This is a fixture definition for the live `obs:automerge:vm-images` E2E, not a production Buildkite pipeline. Its comments say the harness bumps the image pins on an ephemeral fixture pull request and the pins mirror the playground/updatecli shape.

## Execution flow

The pipeline sets `IMAGE_UBUNTU` and `IMAGE_UBUNTU_ARM` to the fixture image identifiers, then runs one step, `e2e-automerge-vm-images noop`, which prints a stable marker. No agent queue, plugin, artifact, dependency, or dynamic upload is specified in this file.

## Inputs, outputs, and access

The YAML has no workflow inputs or secrets. It declares two environment values for the fixture and no artifacts or outputs.

## Source gap

No Buildkite resource for this pipeline was found in the checked-in `catalog-info.yaml`, and this static fixture YAML does not define how or where a remote Buildkite pipeline is provisioned. Remote Buildkite settings and runtime agent configuration were not inspected; do not infer production behavior from this file.

## Sources

- [Fixture pipeline](../pipeline.e2e-automerge-vm-images.yml)
- [GitHub E2E caller](../../.github/workflows/e2e-automerge-vm-images.yml)
- [Automerge E2E workflow notes](../../docs/workflows/e2e-automerge-vm-images.md)

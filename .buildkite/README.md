# Buildkite pipeline documentation

The checked-in Buildkite definitions are E2E fixtures. Their pages describe
the checked-in YAML and identify details configured outside the repository.

- [`oblt-aw-e2e-estc-fail`](docs/oblt-aw-e2e-estc-fail.md): catalog-backed
  intentional failure used to exercise the ESTC Buildkite detective. See the
  [existing provisioning and runtime notes](README.e2e-estc-fail.md).
- [`pipeline.e2e-automerge-vm-images.yml`](docs/pipeline.e2e-automerge-vm-images.md):
  fixture image pins and a no-op step used by the VM-images automerge E2E.

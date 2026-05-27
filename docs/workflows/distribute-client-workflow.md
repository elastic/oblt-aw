# Workflow: `distribute-client-workflow.yml`

## Overview

Source file: [.github/workflows/distribute-client-workflow.yml](../../.github/workflows/distribute-client-workflow.yml)

This workflow creates PRs across target repositories to install, update, or remove the per-org template file set (for example `.github/workflows/trigger-oblt-aw-*.yml`, `.github/workflows/trigger-docs-aw-*.yml`, and any other paths under each org’s `.github/remote-workflow-template/<org-key>/` tree).

## Prerequisites

- Triggered by changes to:
  - `config/**/active-repositories.json` (per-org repo lists; example [config/obs/active-repositories.json](../../config/obs/active-repositories.json))
  - [.github/remote-workflow-template/](../../.github/remote-workflow-template/) (per-org subtrees such as `obs/`, `docs/`)
- Or manually triggered with `workflow_dispatch`.

## Usage

Main jobs:

- `prepare-targets`
- `create-prs`
- `summarize`

Core behavior:

- computes target operations via [scripts/build_target_operations.py](../../scripts/build_target_operations.py)
- clones each target repository
- installs or updates each `dst` from the per-target `files: [{src, dst}, ...]` list
- deletes each path in `remove_files` when templates drop paths or retired client paths no longer apply
- removes all managed `dst` paths when a repository leaves the config (`operation: remove`)
- opens or updates PRs using `peter-evans/create-pull-request`
- emits consolidated summary via [scripts/summarize_pr_results.sh](../../scripts/summarize_pr_results.sh)

### Input and output contracts

- Target config input accepts either:
  - a list of `owner/repo` strings
  - an object with `repositories: [owner/repo, ...]`
- The target builder step exposes:
  - `targets` (JSON matrix entries with `repository`, `operation`, `files`, and for install ops `remove_files`)
  - `has_targets` (`true`/`false`)
  - `install_count`, `remove_count`, `total_count`
- Removal operations are computed by comparing current config against the version at `BASE_REF`.
- PR result artifacts are emitted as `repo|op|url` lines and consumed by the summarize step.

## Configuration

Top-level permissions:

- `contents: read`

Concurrency:

- group `distribute-client-workflow`
- `cancel-in-progress: false`

## References

- Operational details: [docs/operations/distribute-client-workflow.md](../operations/distribute-client-workflow.md)
- Client template: [docs/workflows/oblt-aw-client-template.md](oblt-aw-client-template.md)

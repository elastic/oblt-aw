# Workflow: `distribute-client-workflow.yml`

## Overview

Source file: `.github/workflows/distribute-client-workflow.yml`

This workflow creates PRs across target repositories to install, update, or remove the client entrypoint workflow.

## Prerequisites

- Triggered by changes to:
  - `active-repositories.json`
  - `.github/remote-workflow-template/oblt-aw.yml`
- Or manually triggered with `workflow_dispatch`.

## Usage

Main jobs:

- `prepare-targets`
- `create-prs`
- `summarize`

Core behavior:

- computes target operations via `scripts/build_target_operations.py`
- clones each target repository
- installs or removes `target/.github/workflows/oblt-aw.yml`
- opens or updates PRs using `peter-evans/create-pull-request`
- emits consolidated summary via `scripts/summarize_pr_results.sh`

## Configuration

Top-level permissions:

- `contents: read`

Concurrency:

- group `distribute-client-workflow`
- `cancel-in-progress: false`

## References

- Operational details: `docs/operations/distribute-client-workflow.md`
- Client template: `docs/workflows/oblt-aw-client-template.md`

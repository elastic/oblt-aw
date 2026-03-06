# Distribution Operation: `distribute-client-workflow.yml`

## Overview

Source file: `.github/workflows/distribute-client-workflow.yml`

This workflow distributes or removes the client workflow template (`.github/workflows/oblt-aw.yml`) across repositories listed in `active-repositories.json`.

## Prerequisites

- `active-repositories.json` is maintained with current target repositories.
- `.github/remote-workflow-template/oblt-aw.yml` is the source template.
- Token policy configured for `elastic/oblt-actions/github/create-token@v1`.

## Usage

Triggers:

- `push` to `main` when either of these files changes:
  - `active-repositories.json`
  - `.github/remote-workflow-template/oblt-aw.yml`
- `workflow_dispatch` with optional `force` boolean input.

Execution stages:

1. `prepare-targets`
2. `create-prs`
3. `summarize`

## Configuration

Top-level permissions:

- `contents: read`

Job-specific permissions:

- `create-prs`: `id-token: write`, `contents: read`

Concurrency:

- group: `distribute-client-workflow`
- `cancel-in-progress: false`

## Examples

Manual run with force:

```yaml
on:
  workflow_dispatch:
    inputs:
      force:
        type: boolean
        default: true
```

## References

- Script: `scripts/build_target_operations.py`
- Script: `scripts/summarize_pr_results.sh`
- Client template doc: `docs/workflows/oblt-aw-client-template.md`

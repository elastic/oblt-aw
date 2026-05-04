# Distribution Operation: `distribute-client-workflow.yml`

## Overview

Source file: [.github/workflows/distribute-client-workflow.yml](../../.github/workflows/distribute-client-workflow.yml)

This workflow distributes or removes client files from each org’s subtree under [.github/remote-workflow-template/](../../.github/remote-workflow-template/) across repositories listed in that org’s `config/<org-key>/active-repositories.json` (for example [config/obs/active-repositories.json](../../config/obs/active-repositories.json)). A repository may belong to multiple orgs; destination paths are deduplicated (first org in sorted order wins on collision).

## Prerequisites

- Per-org [active-repositories.json](../../config/obs/active-repositories.json) files under `config/<org-key>/` list current target repositories (union used for distribution).
- Per-org templates under [.github/remote-workflow-template/<org-key>/](../../.github/remote-workflow-template/) are the **only** sources for files installed into consumer repositories (for example `obs/.github/workflows/oblt-aw.yml` → `.github/workflows/oblt-aw.yml`). **Do not edit** [.github/workflows/oblt-aw.yml](../../.github/workflows/oblt-aw.yml) in this repository (see [Client template doc](../workflows/oblt-aw-client-template.md)).
- Token policy configured for [elastic/oblt-actions/github/create-token@v1](https://github.com/elastic/oblt-actions/tree/v1/github/create-token).

## Usage

Triggers:

- `push` to `main` when either of these paths change:
  - `config/**/active-repositories.json` (per-org repo lists)
  - [.github/remote-workflow-template/](../../.github/remote-workflow-template/)
- `workflow_dispatch` with optional `force` boolean input.

Execution stages:

1. `prepare-targets`
2. `create-prs`
3. `summarize`

## Distribution configuration contract (per-org `active-repositories.json`)

[scripts/build_target_operations.py](../../scripts/build_target_operations.py) accepts either of these JSON shapes:

- Object form:

  ```json
  {
    "repositories": [
      "elastic/oblt-aw",
      "elastic/oblt-cli"
    ]
  }
  ```

- List form:

  ```json
  [
    "elastic/oblt-aw",
    "elastic/oblt-cli"
  ]
  ```

Validation and normalization rules:

- `repositories` must resolve to a JSON list.
- Every entry must be a string in `owner/repo` format.
- Entries are normalized (trimmed), de-duplicated, and sorted before processing.
- Invalid entries fail the step with: `Invalid repository entry: ... Expected 'owner/repo'`.

Examples:

- Valid: `"elastic/oblt-aw"`
- Invalid: `"elastic"` (missing slash), `123` (non-string), `{"repo":"elastic/oblt-aw"}` (wrong type)

## `build_target_operations.py` Contract

Inputs (environment variables):

- `CHANGED_FILES_COUNT`: numeric count from the changed-files step.
- `FORCE_DISTRIBUTION`: boolean-like string (`1`, `true`, `yes`, `on` are treated as true).
- `BASE_REF`: prior commit SHA used to read per-org `config/<org-key>/active-repositories.json` paths from git history for removal detection.
- `GITHUB_OUTPUT`: required by GitHub Actions output writing.

Behavior:

- If `CHANGED_FILES_COUNT == 0` and `FORCE_DISTRIBUTION` is false, returns no targets.
- Always generates `install` operations for repositories in the current union of per-org lists (see [scripts/build_target_operations.py](../../scripts/build_target_operations.py)).
- Generates `remove` operations for repositories present at `BASE_REF` but absent from current config.

Workflow outputs written by the script:

- `targets`: JSON array of objects like `{"repository":"owner/repo","operation":"install|remove"}`
- `has_targets`: `true` when at least one operation exists; otherwise `false`
- `install_count`: count of install/update operations
- `remove_count`: count of removal operations
- `total_count`: total operations (`install_count + remove_count`)

## PR Result Artifact and Summary Contract

Each matrix leg writes one artifact line to `pr-result-<index>.txt` with this format:

`repo|op|url`

- `repo`: target repository (`owner/repo`)
- `op`: create-pull-request operation result (for example `created`, `updated`, `skipped`)
- `url`: PR URL when available, or `-` when skipped/no PR

[scripts/summarize_pr_results.sh](../../scripts/summarize_pr_results.sh) reads all `pr-results/*.txt` files, then:

- emits one `::notice` annotation with a compact `repo (operation)` list
- appends a markdown table to `$GITHUB_STEP_SUMMARY` with repository, operation, and PR link

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

- Script: [scripts/build_target_operations.py](../../scripts/build_target_operations.py)
- Script: [scripts/summarize_pr_results.sh](../../scripts/summarize_pr_results.sh)
- Workflow doc: [docs/workflows/distribute-client-workflow.md](../workflows/distribute-client-workflow.md)
- Client template doc: [docs/workflows/oblt-aw-client-template.md](../workflows/oblt-aw-client-template.md)

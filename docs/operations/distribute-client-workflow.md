# Distribution Operation: `distribute-client-workflow.yml`

## Overview

Source file: [.github/workflows/distribute-client-workflow.yml](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/distribute-client-workflow.yml)

This workflow distributes or removes client files from each org’s subtree under [.github/remote-workflow-template/](https://github.com/elastic/oblt-aw/tree/main/.github/remote-workflow-template) across repositories listed in that org’s `config/<org-key>/active-repositories.json` (for example [config/obs/active-repositories.json](https://github.com/elastic/oblt-aw/blob/main/config/obs/active-repositories.json)). A repository may belong to multiple orgs; destination paths are deduplicated (first org in sorted order wins on collision).

## Prerequisites

- Per-org [active-repositories.json](https://github.com/elastic/oblt-aw/blob/main/config/obs/active-repositories.json) files under `config/<org-key>/` list current target repositories (union used for distribution).
- Per-org templates under [.github/remote-workflow-template/<org-key>/](https://github.com/elastic/oblt-aw/tree/main/.github/remote-workflow-template) are the **only** sources for files installed into consumer repositories (for example `obs/.github/workflows/trigger-obs-aw-*.yml` → `.github/workflows/trigger-obs-aw-*.yml`). Edit only under [remote-workflow-template](https://github.com/elastic/oblt-aw/tree/main/.github/remote-workflow-template) (see [Client template doc](../workflows/obs-aw-client-template.md)).
- Template source under [remote-workflow-template](https://github.com/elastic/oblt-aw/tree/main/.github/remote-workflow-template) pins `@main`. At install time, distribute substitutes `uses: elastic/oblt-aw/...@<pin>` from each repo’s `pin-class` (see [release model](release-model.md)). `development` always gets `@main`. `production` gets `tags.current` from [release-pointers.json](https://github.com/elastic/oblt-aw/blob/main/config/release-pointers.json) once `pointers.current.sha` is set **and** that tag exists locally or on `origin`; until then production stays `@main`. If the SHA is set but the tag is missing, prepare fails closed. Distribute **includes** the framework repository (`elastic/oblt-aw`) when it is listed (must be `pin-class: development`).
- Token policy configured for [elastic/oblt-actions/github/create-token@v1](https://github.com/elastic/oblt-actions/tree/v1/github/create-token).
- The minted token must be a GitHub App bot token with permission to write contents and pull requests in each target repository; `create-pull-request` uses this token to create GitHub-verified bot commits.

## Usage

Triggers:

- `push` to `main` when either of these paths change:
  - `config/**/active-repositories.json` (per-org repo lists)
  - `config/release-pointers.json` (production pin retarget after promote)
  - [.github/remote-workflow-template/](https://github.com/elastic/oblt-aw/tree/main/.github/remote-workflow-template)
- `workflow_dispatch` with optional `force` boolean input.

Execution stages:

1. `prepare-targets`
2. `create-prs`
3. `summarize`

PR labels on install and remove PRs:

- Always: `oblt-aw/ai/merge-ready`
- Also when the label already exists in the target repository (Labels API check; the workflow does not create labels):
  - `backport-active-all`
  - `changelog:ci`
  - `skip-changelog` (needed where consumer fragment/changelog gates do not treat `changelog:ci` as a skip, for example beats `fragments`)
- Consumer catalog TokenPolicies must bind `trigger-*-aw-*.yml@*` (not `@refs/heads/main` only) so OIDC minting still works after client workflows land on release/backport branches — see [Registering resources](../onboarding/registering-a-repository.md).

## Distribution configuration contract (per-org `active-repositories.json`)

[scripts/build_target_operations.py](https://github.com/elastic/oblt-aw/blob/main/scripts/build_target_operations.py) expects this JSON shape:

  ```json
  {
    "repositories": [
      {
        "repository": "elastic/oblt-aw",
        "pin-class": "development",
        "workflow-token-policy": "",
        "ai-assets-token-policy": "",
        "pr-actions-detective-workflows": [
          "CI",
          "E2E — intentional Actions failure (pr-actions-detective)"
        ]
      },
      {
        "repository": "elastic/oblt-cli",
        "pin-class": "production",
        "workflow-token-policy": "token-policy-abc123def456",
        "ai-assets-token-policy": ""
      }
    ]
  }
  ```

Validation and normalization rules:

- `repositories` must resolve to a JSON list.
- Every entry is an object with required `repository` (`owner/repo`), `pin-class` (`development` or `production`), `workflow-token-policy` (string; use `""` when Vault auto policy / framework defaults apply for agentic workflow `create-token`), and `ai-assets-token-policy` (string; use `""` when `apm install` can use the job `GITHUB_TOKEN`).
- `pin-class: development` installs keep `uses: elastic/oblt-aw/...@main`. `pin-class: production` installs use `tags.current` from [release-pointers.json](https://github.com/elastic/oblt-aw/blob/main/config/release-pointers.json) once `pointers.current.sha` is set and that tag is published; until then they stay `@main`. Previous-commit repo lists (BASE_REF) may omit `pin-class`; current files must include it.
- `elastic/oblt-aw` must be `pin-class: development`. Parser/CI fail if it is missing, `production`, or any other value.
- Optional `pr-actions-detective-workflows` (list of non-empty strings): GitHub Actions workflow **`name:`** values to monitor for [PR Actions Detective](../workflows/obs-aw-pr-actions-detective.md). When non-empty, distribute installs `trigger-obs-aw-workflow-run.yml` and renders those names into `on.workflow_run.workflows`. When omitted or empty, that trigger is **not** installed (and a previously installed copy is removed). Do not edit the list in the consumer repo — redistribute from this field instead.
- When `workflow-token-policy` is non-empty, consumer `create-token` steps (via `aw-prelude`) use that policy for that repository; when empty, consumer workflows keep Vault auto policy per trigger workflow ref. When `ai-assets-token-policy` is non-empty, [aw-resolve-agentic-assets.yml](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/aw-resolve-agentic-assets.yml) mints an ephemeral token for APM private package clones. Framework workflows `distribute-client-workflow` and `sync-control-plane-dashboard` always use their fixed workflow token policies (`token-policy-63405ab45244` and `token-policy-8b60ba56dd3f`).
- Entries are normalized (trimmed), de-duplicated, and sorted before processing.
- Invalid entries fail the step with: `Invalid repository entry: ... Expected object with 'repository'`.

Examples:

- Valid: `{"repository": "elastic/oblt-aw", "pin-class": "development", "workflow-token-policy": "", "ai-assets-token-policy": "", "pr-actions-detective-workflows": ["CI", "E2E — intentional Actions failure (pr-actions-detective)"]}`
- Valid (no detective): `{"repository": "elastic/oblt-cli", "pin-class": "production", "workflow-token-policy": "", "ai-assets-token-policy": ""}`
- Invalid: `"elastic/oblt-aw"` (bare string), `"elastic"` (missing slash in `repository`), `123` (non-object), `{"repo":"elastic/oblt-aw"}` (wrong key), `{"repository":"elastic/oblt-aw","pin-class":"production"}` (`elastic/oblt-aw` must be development)

## `build_target_operations.py` Contract

Inputs (environment variables):

- `CHANGED_FILES_COUNT`: numeric count from the changed-files step.
- `FORCE_DISTRIBUTION`: boolean-like string (`1`, `true`, `yes`, `on` are treated as true).
- `BASE_REF`: prior commit SHA used to read per-org `config/<org-key>/active-repositories.json` paths from git history for removal detection.
- `GITHUB_OUTPUT`: required by GitHub Actions output writing.

Behavior:

- If `CHANGED_FILES_COUNT == 0`, `FORCE_DISTRIBUTION` is false, and `git diff --name-only` between `BASE_REF` and `HEAD` under `config/`, `.github/remote-workflow-template/`, `scripts/build_target_operations.py`, `scripts/client_workflow_pin.py`, and `scripts/common.py` is empty, returns no targets. The git fallback covers template **renames** (the changed-files action only counts added, modified, and deleted paths) and pin-rewrite script edits.
- Always generates `install` operations for repositories in the current union of per-org lists (see [scripts/build_target_operations.py](https://github.com/elastic/oblt-aw/blob/main/scripts/build_target_operations.py)).
- Each `install` target includes `remove_files`, `pin-class`, and `control-plane-pin` (the git ref substituted into `uses: elastic/oblt-aw/...@<pin>`).
- Each `install` target includes `pr-actions-detective-workflows` from `active-repositories.json`. When that list is empty, `trigger-obs-aw-workflow-run.yml` is omitted from `files` and added to `remove_files`. When non-empty, distribute copies the template then runs [scripts/render_pr_actions_detective_trigger.py](https://github.com/elastic/oblt-aw/blob/main/scripts/render_pr_actions_detective_trigger.py) to replace the workflows placeholder.
- Generates `remove` operations for repositories present at `BASE_REF` but absent from current config.

Workflow outputs written by the script:

- `targets`: JSON array of objects like `{"repository":"owner/repo","operation":"install|remove","pin-class":"development|production","control-plane-pin":"main|v0"}`
- `has_targets`: `true` when at least one operation exists; otherwise `false`
- `install_count`: count of install/update operations
- `remove_count`: count of removal operations
- `total_count`: total operations (`install_count + remove_count`)

## Commit signing

Both the install/update and removal `peter-evans/create-pull-request` steps use `sign-commits: true` with the minted GitHub App token. The action creates commits signed by the app bot; no GPG private key or signing secrets are required.

When the action creates or updates a PR, the matrix leg fails unless its `pull-request-commits-verified` output is `true`. Skipped operations do not require verification. Validate the resulting commit is marked **Verified** in a protected consumer repository before relying on this for its signature policy.

## PR Result Artifact and Summary Contract

Each matrix leg writes one artifact line to `pr-result-<index>.txt` with this format:

`repo|op|url`

- `repo`: target repository (`owner/repo`)
- `op`: create-pull-request operation result (for example `created`, `updated`, `skipped`)
- `url`: PR URL when available, or `-` when skipped/no PR

[scripts/summarize_pr_results.sh](https://github.com/elastic/oblt-aw/blob/main/scripts/summarize_pr_results.sh) reads all `pr-results/*.txt` files, then:

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

- Script: [scripts/build_target_operations.py](https://github.com/elastic/oblt-aw/blob/main/scripts/build_target_operations.py)
- Script: [scripts/summarize_pr_results.sh](https://github.com/elastic/oblt-aw/blob/main/scripts/summarize_pr_results.sh)
- Workflow doc: [docs/workflows/distribute-client-workflow.md](../workflows/distribute-client-workflow.md)
- Client template doc: [docs/workflows/obs-aw-client-template.md](../workflows/obs-aw-client-template.md)

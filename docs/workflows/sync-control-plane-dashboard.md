# Sync Control Plane Dashboard Workflow

## Overview

Source file: [.github/workflows/sync-control-plane-dashboard.yml](../../.github/workflows/sync-control-plane-dashboard.yml)

This workflow creates or updates the **single** Control Plane Dashboard issue in each repository listed in the union of org `config/<org-key>/active-repositories.json` files (for example [config/obs/active-repositories.json](../../config/obs/active-repositories.json)). The dashboard lists workflows **per org** with maturity badges and opt-in checkboxes.

## Prerequisites

- Per-org `config/<org-key>/workflow-registry.json` — workflow metadata (`id`, `name`, `description`, `maturity`, `default_enabled`, optional `section_title`)
- Per-org `config/<org-key>/active-repositories.json` — target repositories for that org’s workflows
- Token policy configured for [elastic/oblt-actions/github/create-token@v1](https://github.com/elastic/oblt-actions/blob/v1/github/create-token/action.yml)

## Usage

Triggers:

- `push` to `main` when any of these paths change:
  - `config/**/workflow-registry.json` and `config/**/active-repositories.json` (per-org trees)
  - [.github/workflows/sync-control-plane-dashboard.yml](../../.github/workflows/sync-control-plane-dashboard.yml)
- `workflow_dispatch`

*Note: Editing the dashboard issue does not trigger this workflow. Dashboard opt-in/opt-out is read at runtime by the ingress (`get-enabled-workflows`); there is no `issues.edited` trigger.*

Execution:

1. **prepare-repos job:** Builds repos matrix from the union of org active-repository lists via [scripts/build_repos_matrix.py](../../scripts/build_repos_matrix.py); outputs JSON for matrix strategy
2. **sync-dashboard job:** Matrix job (one job per repo); each invokes `scripts/sync_control_plane_dashboard.py --repo <owner/repo>`:
    - Search for existing open issue with label `oblt-aw/dashboard`
    - Create or update the issue with title `[oblt-aw] Control Plane Dashboard`, body merged from each applicable org registry (sections per org, three-part checkbox markers)
    - Pin the issue via `gh issue pin` (if limit of 3 pins reached, log and continue)

### `scripts/sync_control_plane_dashboard.py` runtime contract

- `--repo OWNER/REPO` is required. Invalid values that are not in `owner/repo` format fail with exit code `1`.
- Authentication is required via `GH_TOKEN` or `GITHUB_TOKEN`. If neither is set, the script fails with exit code `1`.
- The target repository must be listed in at least one `config/<org-key>/active-repositories.json`. If it is not present in any org config, the script fails with exit code `1` and does not create or update an issue.

Minimal local invocation example:

```bash
export GH_TOKEN="<github-token-with-issue-write-permissions>"
python3 scripts/sync_control_plane_dashboard.py --repo elastic/oblt-aw
```

Expected error behavior examples:

```bash
# Invalid repo format (missing slash) -> exit code 1
python3 scripts/sync_control_plane_dashboard.py --repo oblt-aw

# Repo not configured in any config/<org-key>/active-repositories.json -> exit code 1
python3 scripts/sync_control_plane_dashboard.py --repo elastic/not-in-active-repositories
```

`default_enabled` behavior:

- Used when building checkbox state for workflows that are not present in an existing dashboard body.
- Existing checkbox state in the dashboard issue remains authoritative and is preserved during updates.
- For newly added workflows in `workflow-registry.json`, `default_enabled` determines the initial checkbox state until users edit that workflow's checkbox.

## Configuration

Permissions:

- `contents: read`
- Job: `id-token: write`, `contents: read`

Concurrency:

- group: `sync-control-plane-dashboard`
- `cancel-in-progress: false`

## References

- [docs/operations/control-plane-dashboard.md](../operations/control-plane-dashboard.md) — user instructions
- [docs/operations/control-plane-dashboard-format.md](../operations/control-plane-dashboard-format.md) — dashboard issue format
- [Issue #3732 comment (implementation plan)](https://github.com/elastic/observability-robots/issues/3732#issuecomment-4054356635)

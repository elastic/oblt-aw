# Workflow: Client templates `trigger-docs-aw-*.yml`

## Overview

**Source of truth (edit here only):** [.github/remote-workflow-template/docs/.github/workflows/](../../.github/remote-workflow-template/docs/.github/workflows/)

`distribute-client-workflow` installs these files into consumer repositories for every repository listed under [config/docs/active-repositories.json](../../config/docs/active-repositories.json).

## Split-trigger model

Each Docs menu has its own client template with **only** the GitHub events that can trigger that workflow, then calls the matching reusable workflow in `elastic/oblt-aw`:

```yaml
uses: elastic/oblt-aw/.github/workflows/docs-aw-<name>.yml@main
```

Shared dashboard gating runs inside each `docs-aw-*` reusable workflow via [aw-prelude.yml](aw-prelude.md) (first job), not in the client file.

### Template index

| Client template | Triggers | Reusable workflow |
|-----------------|----------|-------------------|
| `trigger-docs-aw-ai-menu.yml` | `issues` opened; `issue_comment` edited; `workflow_dispatch` (`issue_number` required) | `docs-aw-ai-menu.yml` |
| `trigger-docs-aw-pr-ai-menu-collect.yml` | `pull_request` (opened, reopened, synchronize, ready_for_review) | `docs-aw-pr-ai-menu-collect.yml` |
| `trigger-docs-aw-pr-ai-menu.yml` | `workflow_run` on the collect workflow (completed, success only); `issue_comment` edited; `workflow_dispatch` (`pull_request_number` required) | `docs-aw-pr-ai-menu.yml` |

Route-specific conditions (for example PR vs non-PR issue comments, menu checkbox transitions) are enforced inside the `docs-aw-*` reusable workflows after [aw-prelude](aw-prelude.md) runs.

### Fork PRs and SEC-043 (split-workflow)

Fork PRs cannot post issue comments with a write-capable `GITHUB_TOKEN` from a `pull_request` workflow. `pull_request_target` is unsafe (runs in the base repo with elevated token on untrusted fork events). The PR menu therefore uses a **split-workflow** pattern:

1. **`trigger-docs-aw-pr-ai-menu-collect.yml`** — `pull_request` only; read-only job uploads a `pr-number` artifact (implementation: [docs-aw-pr-ai-menu-collect.yml](../../.github/workflows/docs-aw-pr-ai-menu-collect.yml)).
2. **`trigger-docs-aw-pr-ai-menu.yml`** — `workflow_run` when the collect workflow completes successfully; calls [docs-aw-pr-ai-menu.yml](../../.github/workflows/docs-aw-pr-ai-menu.yml) to download the artifact and post the menu from trusted base-repo context.

Menu checkbox handling (`issue_comment`) and manual refresh (`workflow_dispatch`) stay on `trigger-docs-aw-pr-ai-menu.yml`. Fork checkbox triggers require org membership (enforced in `scripts/docs/pr-menu/evaluate-trigger.js`).

## Configuration

Top-level permissions on every client template:

- `contents: read`

Control-plane `docs-aw-*` workflows declare permissions on **each job** (workflow root is `contents: read` only). Jobs that call `gh-aw-*.lock.yml` should match the upstream lock workflow permissions.

Job-level permissions on `run-aw` must be at least as permissive as the union of all job scopes in the called `docs-aw-*` reusable (see per-template table below).

| Template | `run-aw` job permissions (union of callee jobs) |
|----------|-------------------------------------------------|
| `trigger-docs-aw-ai-menu.yml` | `actions: read`, `contents: read`, `discussions: write`, `issues: write`, `pull-requests: write` |
| `trigger-docs-aw-pr-ai-menu-collect.yml` | `actions: write`, `contents: read` |
| `trigger-docs-aw-pr-ai-menu.yml` | `actions: read`, `checks: read`, `contents: read`, `issues: write`, `pull-requests: write` |

Required secret mapping (both templates):

- `COPILOT_GITHUB_TOKEN: ${{ secrets.COPILOT_GITHUB_TOKEN }}`

## Migration from monolithic `docs-aw.yml`

1. Merge distribution PRs that add `trigger-docs-aw-ai-menu.yml`, `trigger-docs-aw-pr-ai-menu-collect.yml`, and `trigger-docs-aw-pr-ai-menu.yml`.
2. Delete `.github/workflows/docs-aw.yml` in the consumer repository. Remove legacy `docs-aw-ai-menu.yml` / `docs-aw-pr-ai-menu.yml` client files if present; distribution removes paths no longer in the template tree.
3. Update Backstage `workflow_ref` / token policies to reference each installed **`trigger-docs-aw-*.yml`** client workflow file.

## References

- [docs-aw-ai-menu.md](docs-aw-ai-menu.md)
- [docs-aw-pr-ai-menu.md](docs-aw-pr-ai-menu.md)
- [docs/operations/distribute-client-workflow.md](../operations/distribute-client-workflow.md)
- [aw-prelude.md](aw-prelude.md)

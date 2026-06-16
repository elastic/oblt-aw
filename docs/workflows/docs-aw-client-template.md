# Workflow: Client templates `trigger-docs-aw-*.yml`

## Overview

**Source of truth (edit here only):** [.github/remote-workflow-template/docs/.github/workflows/](../../.github/remote-workflow-template/docs/.github/workflows/)

`distribute-client-workflow` installs these files into consumer repositories for every repository listed under [config/docs/active-repositories.json](../../config/docs/active-repositories.json).

## Event-scoped client model

Client templates are grouped by **GitHub event family** so co-triggered routes share one dashboard read per workflow run. Each event-scoped client calls an orchestrator reusable (`docs-aw-event-*.yml`) that runs [aw-prelude.yml](aw-prelude.md) once, then fans out to per-route `docs-aw-*` workflows.

```yaml
uses: elastic/oblt-aw/.github/workflows/docs-aw-event-pull-request.yml@main
```

Per-route dashboard gating uses the required `shared-proceed` input (and related shared allow-list fields) passed from [aw-prelude.yml](aw-prelude.md) via each `docs-aw-event-*` orchestrator.

### Template index

| Client template | Triggers | Orchestrator → routes |
|-----------------|----------|------------------------|
| `trigger-docs-aw-issues.yml` | `issues` opened; `workflow_dispatch` (`issue_number` required) | `docs-aw-event-issues.yml` → `docs-aw-ai-menu.yml` |
| `trigger-docs-aw-issue-comment.yml` | `issue_comment` edited | `docs-aw-event-issue-comment.yml` → `docs-aw-ai-menu.yml`, `docs-aw-pr-ai-menu.yml` |
| `trigger-docs-aw-pull-request.yml` | `pull_request` (opened, reopened, synchronize, ready_for_review) | `docs-aw-event-pull-request.yml` → `docs-aw-pr-ai-menu-collect.yml` |
| `trigger-docs-aw-workflow-run.yml` | `workflow_run` on collect workflow (completed); `workflow_dispatch` (`pull_request_number` required) | `docs-aw-event-workflow-run.yml` → `docs-aw-pr-ai-menu.yml` |

Route-specific conditions (for example PR vs non-PR issue comments, menu checkbox transitions) are enforced inside each `docs-aw-*` reusable workflow after prelude gating.

### Fork PRs and SEC-043 (split-workflow)

Fork PRs cannot post issue comments with a write-capable `GITHUB_TOKEN` from a `pull_request` workflow. `pull_request_target` is unsafe (runs in the base repo with elevated token on untrusted fork events). The PR menu therefore uses a **split-workflow** pattern:

1. **`trigger-docs-aw-pull-request.yml`** — `pull_request` only; uploads a `pr-number` artifact via [docs-aw-pr-ai-menu-collect.yml](../../.github/workflows/docs-aw-pr-ai-menu-collect.yml).
2. **`trigger-docs-aw-workflow-run.yml`** — `workflow_run` when the collect workflow completes successfully; calls [docs-aw-pr-ai-menu.yml](../../.github/workflows/docs-aw-pr-ai-menu.yml) to download the artifact and post the menu from trusted base-repo context.

Menu checkbox handling (`issue_comment`) uses `trigger-docs-aw-issue-comment.yml`. Manual refresh uses `workflow_dispatch` on `trigger-docs-aw-issues.yml` (issue menu) or `trigger-docs-aw-workflow-run.yml` (PR menu). Fork checkbox triggers require org membership (enforced in `scripts/docs/pr-menu/evaluate-trigger.js`).

## Configuration

Top-level permissions on every client template:

- `contents: read`

Control-plane `docs-aw-*` workflows declare permissions on **each job** (workflow root is `contents: read` only). Jobs that call `gh-aw-*.lock.yml` should match the upstream lock workflow permissions.

Job-level permissions on `run-aw` must be at least as permissive as the union of all route jobs in the called event orchestrator (see table below).

| Client template | `run-aw` job permissions (union of callee jobs) |
|-----------------|-----------------------------------------------|
| `trigger-docs-aw-issues.yml` | `actions: read`, `contents: read`, `discussions: write`, `issues: write`, `pull-requests: write` |
| `trigger-docs-aw-issue-comment.yml` | `actions: read`, `checks: read`, `contents: read`, `discussions: write`, `issues: write`, `pull-requests: write` |
| `trigger-docs-aw-pull-request.yml` | `actions: write`, `contents: read` |
| `trigger-docs-aw-workflow-run.yml` | `actions: read`, `checks: read`, `contents: read`, `issues: write`, `pull-requests: write` |

Optional secret mapping (keep forwarding for backward compatibility when present):

- `COPILOT_GITHUB_TOKEN: ${{ secrets.COPILOT_GITHUB_TOKEN }}`

## Migration from per-route client templates

1. Merge distribution PRs that replace `trigger-docs-aw-ai-menu.yml`, `trigger-docs-aw-pr-ai-menu-collect.yml`, and `trigger-docs-aw-pr-ai-menu.yml` with the four event-scoped clients above.
2. Distribution removes client paths that are no longer in the template tree.
3. Update Backstage `workflow_ref` / token policies to reference the new client workflow files.

## Migration from monolithic `docs-aw.yml`

1. Merge distribution PRs that add event-scoped `trigger-docs-aw-*.yml` files.
2. Delete `.github/workflows/docs-aw.yml` in the consumer repository. Remove legacy per-route client files if present; distribution drops paths that are no longer in the template tree.
3. Update Backstage `workflow_ref` / token policies to reference each installed **`trigger-docs-aw-*.yml`** client workflow file.

## References

- [docs-aw-ai-menu.md](docs-aw-ai-menu.md)
- [docs-aw-pr-ai-menu.md](docs-aw-pr-ai-menu.md)
- [docs/operations/distribute-client-workflow.md](../operations/distribute-client-workflow.md)
- [aw-prelude.md](aw-prelude.md)
- [oblt-aw-client-template.md](oblt-aw-client-template.md)

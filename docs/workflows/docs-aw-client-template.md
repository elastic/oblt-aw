# Workflow: Client templates `trigger-docs-aw.yml` and `docs-aw.yml`

## Overview

Consumer Documentation repositories install workflows from [`.github/remote-workflow-template/docs/.github/workflows/`](../../.github/remote-workflow-template/docs/.github/workflows/) via [distribute-client-workflow](distribute-client-workflow.md).

Flow: **`trigger-docs-aw.yml`** (events) → **`docs-aw.yml`** (`workflow_dispatch`) → **`docs-aw-ingress.yml`** (routing).

Control-plane reusables are referenced from `elastic/oblt-aw`:

```yaml
uses: elastic/oblt-aw/.github/workflows/docs-aw-ingress.yml@main
```

Shared dashboard gating and prelude run in ingress, not in the client trigger file.

## Installed client workflows

| File | Triggers | Role |
|------|----------|------|
| `trigger-docs-aw.yml` | `issues` opened; `issue_comment` edited; `pull_request` (opened, reopened, synchronize, ready_for_review); `workflow_run` on this workflow (completed, success); `workflow_dispatch` (optional `issue_number`, `pull_request_number`) | Dispatches `docs-aw.yml` with relayed event JSON |
| `docs-aw.yml` | `workflow_dispatch` only | Entrypoint; calls `docs-aw-ingress.yml` |

Route-specific conditions (for example PR vs non-PR issue comments, menu checkbox transitions) are enforced inside the `docs-aw-*` reusable workflows after ingress routing.

## Split PR menu pattern

The PR AI menu uses a fork-safe collect leg and a privileged post leg within one trigger:

1. **`pull_request`** on `trigger-docs-aw.yml` → ingress `route-pr-ai-menu-collect` uploads a `pr-number` artifact.
2. **`workflow_run`** when that trigger completes successfully (`workflow_run.event == pull_request`) → ingress `route-pr-ai-menu` downloads the artifact and posts the menu from trusted base-repo context.

Menu checkbox handling (`issue_comment`) and manual refresh (`workflow_dispatch`) use the same unified trigger.

On `pull_request` and on the privileged `workflow_run` leg (`workflow_run.event == pull_request`), the trigger posts commit status context `docs-aw/entrypoint` on the PR head SHA with `target_url` pointing at the dispatched `docs-aw.yml` run (`runUrlHtml` from `workflow-dispatch`). This is traceability only; the trigger does not wait for ingress or routed workflows to finish.

## Permissions

Control-plane `docs-aw-*` workflows declare permissions on **each job** (workflow root is `contents: read` only).

| Client workflow | Job permissions (minimum) |
|-----------------|---------------------------|
| `trigger-docs-aw.yml` | `actions: write`, `contents: read`, `id-token: write`, `statuses: write` (dispatch job; status used for PR traceability) |
| `docs-aw.yml` | `actions: write`, `contents: read`, `id-token: write`, `issues: read`, `pull-requests: read` (ingress job; routed workflows may need more) |

Routed workflows (`docs-aw-ai-menu.yml`, `docs-aw-pr-ai-menu.yml`) require `issues: write`, `pull-requests: write`, and related scopes on agent jobs.

## Migration from per-workflow `trigger-docs-aw-*.yml`

1. Merge distribution PRs that add `trigger-docs-aw.yml` and `docs-aw.yml`.
2. Delete legacy `trigger-docs-aw-ai-menu.yml`, `trigger-docs-aw-pr-ai-menu-collect.yml`, and `trigger-docs-aw-pr-ai-menu.yml` from the consumer repository.
3. Update Backstage `workflow_ref` / token policies to reference **`trigger-docs-aw.yml`**.

## References

- [docs-aw-ingress.md](docs-aw-ingress.md)
- [docs-aw-ai-menu.md](docs-aw-ai-menu.md)
- [docs-aw-pr-ai-menu.md](docs-aw-pr-ai-menu.md)
- [aw-prelude.md](aw-prelude.md)

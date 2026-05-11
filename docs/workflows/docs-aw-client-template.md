# Workflow: Client Template `docs-aw.yml`

## Overview

**Source of truth (edit here only):** [.github/remote-workflow-template/docs/.github/workflows/docs-aw.yml](../../.github/remote-workflow-template/docs/.github/workflows/docs-aw.yml)

`distribute-client-workflow` installs this file into consumer repositories as `.github/workflows/docs-aw.yml` for every repository listed under [config/docs/active-repositories.json](../../config/docs/active-repositories.json).

## Usage

Triggers (must stay aligned with [docs-aw-ingress](docs-aw-ingress.md) routing):

- `issues` (`opened`) — posts the issue AI menu
- `issue_comment` (`edited`) — checkbox transitions on the issue AI menu (non-PR issues)
- `pull_request_target` (`opened`, `reopened`, `synchronize`, `ready_for_review`) — posts and refreshes the PR AI menu
- `workflow_dispatch` — manual refresh; provide `issue_number` and/or `pull_request_number` (at least one required; enforced in ingress)

Execution flow:

1. **run-docs-aw** calls [elastic/oblt-aw/.github/workflows/docs-aw-ingress.yml@main](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/docs-aw-ingress.yml). The ingress routes to reusable [.github/workflows/docs-ai-menu.yml](../../.github/workflows/docs-ai-menu.yml) and [.github/workflows/docs-pr-ai-menu.yml](../../.github/workflows/docs-pr-ai-menu.yml). Menu automation scripts live under `scripts/docs/`; reusable workflows check out **`elastic/oblt-aw`** with **sparse checkout** of only `scripts/docs/issue-menu` or `scripts/docs/pr-menu` (shallow `fetch-depth: 1`).

## Configuration

Top-level permissions:

- `contents: read`

Job-level permissions (`run-docs-aw`; must stay at least as permissive as nested ingress and downstream reusable workflows):

- `actions: read`
- `checks: read`
- `contents: read`
- `discussions: write`
- `id-token: write`
- `issues: write`
- `pull-requests: write`

Required secret mapping:

- `COPILOT_GITHUB_TOKEN: ${{ secrets.COPILOT_GITHUB_TOKEN }}`

## References

- Distribution process: [docs/operations/distribute-client-workflow.md](../operations/distribute-client-workflow.md)
- Ingress: [docs/workflows/docs-aw-ingress.md](docs-aw-ingress.md)

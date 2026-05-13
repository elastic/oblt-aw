# Workflow: `docs-ai-menu.yml`

## Overview

Source file: [.github/workflows/docs-ai-menu.yml](../../.github/workflows/docs-ai-menu.yml)

Reusable implementation for the Docs issue AI menu. The Docs client template (`docs-aw.yml`) calls `docs-aw-ingress`, and ingress routes supported issue events to this workflow.

## Prerequisites

- Triggered via `workflow_call` from [docs/workflows/docs-aw-ingress.md](docs-aw-ingress.md).
- Optional secret input: `COPILOT_GITHUB_TOKEN` (`required: false` at this workflow boundary).

## Usage

Jobs and routing behavior:

1. `post-menu` posts or refreshes the issue AI menu when the routed event is `issues` or `workflow_dispatch`.
2. `evaluate-trigger` runs on routed `issue_comment` events for non-PR issues when an existing AI menu bot comment was edited (`<!-- docs-ai-menu:start -->` and `<!-- docs-ai-menu:end -->` markers).
3. `run-docs-triage` calls `elastic/docs-actions/.github/workflows/gh-aw-issue-triage.lock.yml@v1` when `triage_triggered == 'true'`.
4. `run-docs-issue-scope` calls `elastic/docs-actions/.github/workflows/gh-aw-docs-issue-scope.lock.yml@v1` when `issue_scope_triggered == 'true'`.
5. Refresh jobs update the AI menu comment after trigger evaluation and after each downstream run.

Menu comment automation checks out `elastic/oblt-aw` with sparse checkout of `scripts/docs/issue-menu`.

## Configuration

Top-level permissions:

- `contents: read`

Key job-level permissions:

- Menu comment/update jobs: `contents: read`, `issues: write`
- Downstream docs-actions jobs: `actions: read`, `contents: read`, `discussions: write`, `issues: write`, `pull-requests: write`

## API / Interface

`workflow_call` contract:

- Secret: `COPILOT_GITHUB_TOKEN` (`required: false`)

## References

- Ingress routing: [docs/workflows/docs-aw-ingress.md](docs-aw-ingress.md)
- Client template entrypoint: [docs/workflows/docs-aw-client-template.md](docs-aw-client-template.md)
- Menu scripts: [scripts/docs/issue-menu/](../../scripts/docs/issue-menu/)

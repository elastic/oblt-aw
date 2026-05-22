# Workflow: `docs-aw-pr-ai-menu.yml`

## Overview

Source file: [.github/workflows/docs-aw-pr-ai-menu.yml](../../.github/workflows/docs-aw-pr-ai-menu.yml)

Reusable implementation for the Docs PR AI menu. The client template `trg-docs-aw-pr-ai-menu.yml` calls this workflow on supported PR events.

## Prerequisites

- Triggered via `workflow_call` from [trg-docs-aw-pr-ai-menu.yml](../../.github/remote-workflow-template/docs/.github/workflows/trg-docs-aw-pr-ai-menu.yml) (distributed client template).
- Optional secret input: `COPILOT_GITHUB_TOKEN` (`required: false` at this workflow boundary).

## Usage

Jobs and routing behavior:

1. `post-menu` posts or refreshes the PR AI menu when the routed event is `pull_request_target` or `workflow_dispatch`.
2. `evaluate-trigger` runs on routed `issue_comment` events for PRs when an existing AI menu bot comment was edited (`<!-- docs-pr-ai-menu:start -->` and `<!-- docs-pr-ai-menu:end -->` markers).
3. `run-docs-review` calls `elastic/docs-actions/.github/workflows/gh-aw-docs-review.lock.yml@v1` when `docs_review_triggered == 'true'`, with `review-scope: repo-wide-markdown`.
4. Refresh jobs update the AI PR menu comment after trigger evaluation and after the downstream review run.

Menu comment automation checks out `elastic/oblt-aw` with sparse checkout of `scripts/docs/pr-menu`.

## Configuration

Top-level permissions:

- `contents: read`

Key job-level permissions:

- Menu comment/update jobs: `checks: read`, `contents: read`, `issues: write`, `pull-requests: write`
- Downstream docs-actions job: `actions: read`, `contents: read`, `discussions: write`, `issues: write`, `pull-requests: write`

## API / Interface

`workflow_call` contract:

- Secret: `COPILOT_GITHUB_TOKEN` (`required: false`)

## References

- Client templates: [docs/workflows/docs-aw-client-template.md](docs-aw-client-template.md)
- Prelude gating: [docs/workflows/aw-prelude.md](aw-prelude.md)
- Menu scripts: [scripts/docs/pr-menu/](../../scripts/docs/pr-menu/)

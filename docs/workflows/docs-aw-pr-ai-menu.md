# Workflow: `docs-aw-pr-ai-menu.yml`

## Overview

Source file: [.github/workflows/docs-aw-pr-ai-menu.yml](../../.github/workflows/docs-aw-pr-ai-menu.yml)

Reusable implementation for the Docs PR AI menu. Event-scoped client templates call `docs-aw-event-issue-comment.yml` or `docs-aw-event-workflow-run.yml`, which fan out to this route on supported events.

## Prerequisites

- Triggered via `workflow_call` from [docs-aw-event-workflow-run.yml](../../.github/workflows/docs-aw-event-workflow-run.yml) or [docs-aw-event-issue-comment.yml](../../.github/workflows/docs-aw-event-issue-comment.yml) after client templates in [docs-aw-client-template.md](docs-aw-client-template.md).

## Usage

Jobs and routing behavior:

1. `post-menu` posts or refreshes the PR AI menu when the routed event is a successful `workflow_run` of [trigger-docs-aw-pull-request.yml](../../.github/remote-workflow-template/docs/.github/workflows/trigger-docs-aw-pull-request.yml) or `workflow_dispatch`. The collect leg uses fork-safe `pull_request`; the privileged leg downloads the PR number artifact and never uses `pull_request_target`.
2. `evaluate-trigger` runs on routed `issue_comment` events for PRs when an existing AI menu bot comment was edited (`<!-- docs-pr-ai-menu:start -->` and `<!-- docs-pr-ai-menu:end -->` markers). On fork PRs, only organization members may trigger the docs review path.
3. `run-docs-review` calls `elastic/docs-actions/.github/workflows/gh-aw-docs-review.lock.yml@v1` when `docs_review_triggered == 'true'`, with `review-scope: repo-wide-markdown`.
4. Refresh jobs update the AI PR menu comment after trigger evaluation and after the downstream review run.

Menu comment automation checks out `elastic/oblt-aw` with sparse checkout of `scripts/docs/pr-menu`.

Menu copy references for docs-actions workflows use the `gh-aw-*` docs:

- Docs review: [elastic/docs-actions/.github/workflows/gh-aw-docs-review.md](https://github.com/elastic/docs-actions/blob/main/.github/workflows/gh-aw-docs-review.md)

## Configuration

Top-level permissions:

- `contents: read`

Key job-level permissions:

- Menu comment/update jobs: `checks: read`, `contents: read`, `issues: write`, `pull-requests: write`
- Downstream docs-actions job: `actions: read`, `contents: read`, `discussions: write`, `issues: write`, `pull-requests: write`

## API / Interface

`workflow_call` contract:


## References

- Client templates: [docs/workflows/docs-aw-client-template.md](docs-aw-client-template.md)
- Prelude gating: [docs/workflows/aw-prelude.md](aw-prelude.md)
- Menu scripts: [scripts/docs/pr-menu/](../../scripts/docs/pr-menu/)

# Workflow: `docs-aw-ai-menu.yml`

## Overview

Source file: [.github/workflows/docs-aw-ai-menu.yml](../../.github/workflows/docs-aw-ai-menu.yml)

Reusable implementation for the Docs issue AI menu. Event-scoped client templates call `docs-aw-event-issues.yml` or `docs-aw-event-issue-comment.yml`, which fan out to this route on supported events.

## Prerequisites

- Triggered via `workflow_call` from [docs-aw-event-issues.yml](../../.github/workflows/docs-aw-event-issues.yml) or [docs-aw-event-issue-comment.yml](../../.github/workflows/docs-aw-event-issue-comment.yml) after client templates in [docs-aw-client-template.md](docs-aw-client-template.md).

## Usage

Jobs and routing behavior:

1. `post-menu` posts or refreshes the issue AI menu when the routed event is `issues` or `workflow_dispatch`.
2. `evaluate-trigger` runs on routed `issue_comment` events for non-PR issues when an existing AI menu bot comment was edited (`<!-- docs-ai-menu:start -->` and `<!-- docs-ai-menu:end -->` markers).
3. `run-docs-triage` calls `elastic/docs-actions/.github/workflows/gh-aw-issue-triage.lock.yml@v1` when `triage_triggered == 'true'`.
4. `run-docs-issue-scope` calls `elastic/docs-actions/.github/workflows/gh-aw-issue-scope.lock.yml@v1` when `issue_scope_triggered == 'true'`.
5. Refresh jobs update the AI menu comment after trigger evaluation and after each downstream run.

Menu comment automation checks out `elastic/oblt-aw` with sparse checkout of `scripts/docs/issue-menu`.

Menu copy references for docs-actions workflows use the `gh-aw-*` docs:

- Triage: [elastic/docs-actions/.github/workflows/gh-aw-issue-triage.md](https://github.com/elastic/docs-actions/blob/main/.github/workflows/gh-aw-issue-triage.md)
- Scope: [elastic/docs-actions/.github/workflows/gh-aw-issue-scope.md](https://github.com/elastic/docs-actions/blob/main/.github/workflows/gh-aw-issue-scope.md)

## Configuration

Top-level permissions:

- `contents: read`

Key job-level permissions:

- Menu comment/update jobs: `contents: read`, `issues: write`
- Downstream docs-actions jobs: `actions: read`, `contents: read`, `discussions: write`, `issues: write`, `pull-requests: write`

## API / Interface

`workflow_call` contract:

- `shared-proceed` (`string`, required) — dashboard gate result for this route from
  `aw-prelude`; the route runs only when this is `true`.
- `shared-allowed-pr-authors-json` (`string`, required) — JSON array of allowed PR bot
  logins from the prelude. This route currently receives the shared value for a
  consistent reusable-workflow interface.
- `shared-allowed-pr-authors-csv` (`string`, required) — comma-separated form of the
  allowed PR bot logins.
- `shared-allowed-issue-authors-json` (`string`, required) — JSON array of allowed
  issue bot logins.
- `shared-allowed-issue-authors-csv` (`string`, required) — comma-separated form of
  the allowed issue bot logins.
- `shared-token-policy` (`string`, required) — repository `workflow-token-policy`
  resolved by the prelude; empty when no repository-specific policy is configured.

The event-scoped orchestrator supplies these values from the shared prelude. A caller
that already has equivalent prelude outputs can invoke the reusable workflow as
follows:

```yaml
jobs:
  ai-menu:
    uses: ./.github/workflows/docs-aw-ai-menu.yml
    with:
      shared-proceed: ${{ fromJSON(needs.run-aw-prelude.outputs.proceed-by-workflow)['docs-aw-ai-menu.yml'] }}
      shared-allowed-pr-authors-json: ${{ needs.run-aw-prelude.outputs.allowed-pr-authors-json }}
      shared-allowed-pr-authors-csv: ${{ needs.run-aw-prelude.outputs.allowed-pr-authors-csv }}
      shared-allowed-issue-authors-json: ${{ needs.run-aw-prelude.outputs.allowed-issue-authors-json }}
      shared-allowed-issue-authors-csv: ${{ needs.run-aw-prelude.outputs.allowed-issue-authors-csv }}
      shared-token-policy: ${{ needs.run-aw-prelude.outputs.token-policy }}
```

## References

- Client templates: [docs/workflows/docs-aw-client-template.md](docs-aw-client-template.md)
- Prelude gating: [docs/workflows/aw-prelude.md](aw-prelude.md)
- Menu scripts: [scripts/docs/issue-menu/](../../scripts/docs/issue-menu/)

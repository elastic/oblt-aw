# Workflow: `docs-aw-ingress.yml`

## Overview

Reusable workflow ([.github/workflows/docs-aw-ingress.yml](../../.github/workflows/docs-aw-ingress.yml)) invoked from distributed [.github/remote-workflow-template/docs/.github/workflows/docs-aw.yml](../../.github/remote-workflow-template/docs/.github/workflows/docs-aw.yml). It routes the caller’s event to either the issue menu reusable ([.github/workflows/docs-ai-menu.yml](../../.github/workflows/docs-ai-menu.yml)) or the PR menu reusable ([.github/workflows/docs-pr-ai-menu.yml](../../.github/workflows/docs-pr-ai-menu.yml)).

## Routing summary

| Condition | Target reusable |
| --- | --- |
| `issues` `opened`, or `issue_comment` `edited` on a non-PR issue, or `workflow_dispatch` with `issue_number` set | [.github/workflows/docs-ai-menu.yml](../../.github/workflows/docs-ai-menu.yml) |
| `pull_request_target`, or `issue_comment` `edited` on a PR, or `workflow_dispatch` with `pull_request_number` set | [.github/workflows/docs-pr-ai-menu.yml](../../.github/workflows/docs-pr-ai-menu.yml) |
| `workflow_dispatch` with both inputs empty | `invalid-workflow-dispatch` job fails the run |

Unsupported event or action combinations are rejected by the `unsupported-trigger` job (mirrors the observability ingress pattern).

## References

- Client template: [docs/workflows/docs-aw-client-template.md](docs-aw-client-template.md)
- Observability ingress (pattern reference): [docs/workflows/oblt-aw-ingress.md](oblt-aw-ingress.md)

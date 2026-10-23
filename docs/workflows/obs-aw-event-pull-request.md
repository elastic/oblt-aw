# Workflow: `obs-aw-event-pull-request.yml`

## At a glance

| | |
| --- | --- |
| Platform | GitHub Actions reusable workflow |
| Source | [`.github/workflows/obs-aw-event-pull-request.yml`](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/obs-aw-event-pull-request.yml) |
| Trigger | `workflow_call`, invoked by the Observability pull-request client template |

## Purpose

Routes pull-request events through one shared prelude to automerge and dependency review, while excluding dedicated same-repository E2E fixture pull requests where appropriate.

## Execution flow

`run-aw-prelude` evaluates both route gates and loads the allowed PR-author lists. The `automerge` job runs for eligible `opened`, `synchronize`, `reopened`, or `labeled` events from allow-listed authors when the `oblt-aw/ai/merge-ready` label is present. It excludes the ESTC, PR Actions Detective, and dependency-review E2E fixture branches. The `dependency-review` job runs for eligible `opened`, `synchronize`, or `reopened` events and excludes the ESTC and PR Actions Detective fixtures; the dependency-review fixture is intentionally not excluded from this route.

Both routes also require their respective `proceed-by-workflow` gate and call the corresponding reusable workflow with shared author lists and token policy.

## Inputs, outputs, and access

No inputs, outputs, or secrets are declared. Top-level permissions are `contents: read`; called jobs receive route-specific write permissions and OIDC access.

## Sources

- [Event orchestrator](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/obs-aw-event-pull-request.yml)
- [Automerge](obs-aw-automerge.md)
- [Dependency review](obs-aw-dependency-review.md)
- [Observability client templates](obs-aw-client-template.md)
- [Shared prelude](aw-prelude.md)

# Workflow: Client templates `trigger-security-aw-*.yml`

## Overview

**Source of truth (edit here only):** [.github/remote-workflow-template/security/.github/workflows/](https://github.com/elastic/oblt-aw/tree/main/.github/remote-workflow-template/security/.github/workflows)

`distribute-client-workflow` installs these files into consumer repositories for every repository listed under [config/security/active-repositories.json](https://github.com/elastic/oblt-aw/blob/main/config/security/active-repositories.json).

The Security org registry ([config/security/workflow-registry.json](https://github.com/elastic/oblt-aw/blob/main/config/security/workflow-registry.json)) opts into two shared services with `include_common`: `estc-pr-buildkite-detective` and `dependency-review`. Their definitions live in [config/common/services.json](https://github.com/elastic/oblt-aw/blob/main/config/common/services.json), and the implementation stays in the Observability wrappers [obs-aw-estc-pr-buildkite-detective](obs-aw-estc-pr-buildkite-detective.md) and [obs-aw-dependency-review](obs-aw-dependency-review.md). The `security-aw-event-*` orchestrators pass `org-key: security` to `aw-prelude` and `shared-org-key: security` to each wrapper. The dashboard gate ids are `security:estc-pr-buildkite-detective` and `security:dependency-review`. The `issues` and `issue_comment` templates support **Control Plane dashboard audit only**. To opt in to more shared services, follow [Opt in common services](../admin-guide/opt-in-common-services.md).

This org key (`security`) is not the Observability registry id `obs:security` (detector / triage / fixer under `config/obs/`).

## Event-scoped client model

```yaml
uses: elastic/oblt-aw/.github/workflows/security-aw-event-issues.yml@main
```

Template source stays `@main`. Distribute substitutes the production moving major for `pin-class: production` installs after the first promote; `development` installs keep `@main` (see [release-model](../operations/release-model.md)).

### Template index

| Client template | Triggers | Orchestrator → jobs |
|-----------------|----------|---------------------|
| `trigger-security-aw-issues.yml` | `issues` opened/edited; `workflow_dispatch` | `security-aw-event-issues.yml` → dashboard-audit (edited + `oblt-aw/dashboard`) |
| `trigger-security-aw-issue-comment.yml` | `issue_comment` created (job runs only when the issue has `oblt-aw/dashboard`) | `security-aw-event-issue-comment.yml` → dashboard-audit-reason |
| `trigger-security-aw-status.yml` | `status` failure with a Buildkite context | `security-aw-event-status.yml` → `estc-pr-buildkite-detective` |
| `trigger-security-aw-pull-request.yml` | `pull_request` opened/synchronize/reopened | `security-aw-event-pull-request.yml` → `dependency-review` |

## Configuration

Top-level permissions on every client template:

- `contents: read`

| Client template | Entrypoint job id | Job permissions |
|-----------------|-------------------|-----------------|
| `trigger-security-aw-issues.yml` | `run-security-aw-issues` | `contents: read`, `issues: write` |
| `trigger-security-aw-issue-comment.yml` | `run-security-aw-issue-comment` | `contents: read`, `issues: write` |
| `trigger-security-aw-status.yml` | `run-security-aw-status` | `actions: read`, `contents: read`, `copilot-requests: write`, `id-token: write`, `issues: write`, `pull-requests: write` |
| `trigger-security-aw-pull-request.yml` | `run-security-aw-pull-request` | `actions: read`, `contents: read`, `copilot-requests: write`, `id-token: write`, `issues: write`, `pull-requests: write` |

## References

- [Multi-org design](../architecture/multi-org-agentic-workflows.md)
- [docs-aw-client-template.md](docs-aw-client-template.md)
- [obs-aw-client-template.md](obs-aw-client-template.md)
- [docs/operations/distribute-client-workflow.md](../operations/distribute-client-workflow.md)

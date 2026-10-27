# Workflow: Client templates `trigger-security-aw-*.yml`

## Overview

**Source of truth (edit here only):** [.github/remote-workflow-template/security/.github/workflows/](https://github.com/elastic/oblt-aw/tree/main/.github/remote-workflow-template/security/.github/workflows)

`distribute-client-workflow` installs these files into consumer repositories for every repository listed under [config/security/active-repositories.json](https://github.com/elastic/oblt-aw/blob/main/config/security/active-repositories.json).

The Security org registry starts empty ([config/security/workflow-registry.json](https://github.com/elastic/oblt-aw/blob/main/config/security/workflow-registry.json)). Client templates currently support **Control Plane dashboard audit only**. When Security adds agentic routes, extend the matching `security-aw-event-*` orchestrators with `aw-prelude` and route jobs (same pattern as [docs-aw-client-template](docs-aw-client-template.md) / [obs-aw-client-template](obs-aw-client-template.md)).

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

## Configuration

Top-level permissions by client template:

- `trigger-security-aw-issues.yml`: `contents: read`
- `trigger-security-aw-issue-comment.yml`: `contents: read`, `issues: read`

| Client template | Entrypoint job id | Job permissions |
|-----------------|-------------------|-----------------|
| `trigger-security-aw-issues.yml` | `run-security-aw-issues` | `contents: read`, `issues: write` |
| `trigger-security-aw-issue-comment.yml` | `run-security-aw-issue-comment` | `contents: read`, `issues: write` |

## References

- [Multi-org design](../architecture/multi-org-agentic-workflows.md)
- [docs-aw-client-template.md](docs-aw-client-template.md)
- [obs-aw-client-template.md](obs-aw-client-template.md)
- [docs/operations/distribute-client-workflow.md](../operations/distribute-client-workflow.md)

# Workflow: Client templates `trigger-oblt-aw-*.yml`

## Overview

**Source of truth (edit here only):** [.github/remote-workflow-template/obs/.github/workflows/](../../.github/remote-workflow-template/obs/.github/workflows/)

## Event-scoped client model

Client templates are grouped by **GitHub event family** so co-triggered routes share one dashboard read and one allow-list load per workflow run. Each event-scoped client calls an orchestrator reusable (`oblt-aw-event-*.yml`) that runs [aw-prelude.yml](aw-prelude.md) once, then fans out to per-route `oblt-aw-*` workflows.

```yaml
uses: elastic/oblt-aw/.github/workflows/oblt-aw-event-pull-request.yml@main
```

Per-route dashboard gating uses the required `shared-proceed` input (and related shared allow-list fields) passed from [aw-prelude.yml](aw-prelude.md) via each `oblt-aw-event-*` orchestrator.

### Architecture

```mermaid
flowchart TB
  subgraph Consumer["Consumer .github/workflows/"]
    EVT["GitHub event"]
    C_PR["trigger-oblt-aw-pull-request.yml\non: pull_request"]
    C_ISS["trigger-oblt-aw-issues.yml\non: issues, workflow_dispatch"]
    C_COM["trigger-oblt-aw-issue-comment.yml\non: issue_comment"]
    C_SCH["trigger-oblt-aw-schedule.yml\ntrigger-oblt-aw-status.yml"]
    DASH["Issue: [oblt-aw] Control Plane Dashboard"]
    EVT --> C_PR
    EVT --> C_ISS
    EVT --> C_COM
    EVT -.->|on: no match| C_SCH
  end

  subgraph OBLT["elastic/oblt-aw"]
    ORCH["oblt-aw-event-* orchestrator"]
    CTX["aw-prelude"]
    R["oblt-aw-* route"]
    AG["Agent steps"]
    LOCK["Upstream gh-aw lock"]
    ORCH --> CTX
    ORCH --> R
    R --> AG --> LOCK
  end

  DASH -.->|checkboxes| CTX
  C_PR --> ORCH
  C_ISS --> ORCH
  C_COM --> ORCH
  C_SCH --> ORCH
```

Full platform view (distribution, dashboard sync, before/after ingress): [architecture overview — split-trigger diagrams](../architecture/overview.md#split-trigger-vs-monolithic-ingress).

### Template index

| Client template | Triggers | Reusable workflow |
|-----------------|----------|-------------------|
| `trigger-oblt-aw-pull-request.yml` | `pull_request` (opened, synchronize, reopened, labeled) | `oblt-aw-event-pull-request.yml` → automerge, dependency-review |
| `trigger-oblt-aw-issues.yml` | `issues` (opened, labeled), `workflow_dispatch` | `oblt-aw-event-issues.yml` → issue-triage, duplicate-issue-detector, security triage/fixer, resource triage/fixer |
| `trigger-oblt-aw-issue-comment.yml` | `issue_comment` created | `oblt-aw-event-issue-comment.yml` → issue-fixer, mention-in-issue |
| `trigger-oblt-aw-schedule.yml` | `schedule` (daily 06:00 UTC), `workflow_dispatch` | `oblt-aw-event-schedule.yml` → agent-suggestions, autodoc, security-detector, resource-not-accessible detector |
| `trigger-oblt-aw-status.yml` | `status` (Buildkite failure only, job `if`) | `oblt-aw-event-status.yml` → estc-pr-buildkite-detective |

Route-specific conditions (labels, `/ai` comment prefix, allow-listed PR authors, and so on) are enforced inside each `oblt-aw-*` reusable workflow after prelude gating.

## Configuration

Top-level permissions on every client template:

- `contents: read`

Control-plane `oblt-aw-*` workflows declare permissions on **each job** (workflow root is `contents: read` only). Jobs that call `gh-aw-*.lock.yml` should match the upstream lock workflow permissions.

Job-level permissions on `run-aw` must be at least as permissive as the union of all route jobs in the called event orchestrator (see table below).

| Client template | `run-aw` job permissions (union of callee jobs) |
|-----------------|-----------------------------------------------|
| `trigger-oblt-aw-pull-request.yml` | `actions: read`, `contents: write`, `discussions: write`, `id-token: write`, `issues: write`, `pull-requests: write` |
| `trigger-oblt-aw-issues.yml` | `actions: read`, `contents: write`, `discussions: write`, `id-token: write`, `issues: write`, `pull-requests: write` |
| `trigger-oblt-aw-issue-comment.yml` | `actions: read`, `contents: write`, `discussions: write`, `issues: write`, `pull-requests: write` |
| `trigger-oblt-aw-schedule.yml` | `actions: read`, `contents: write`, `id-token: write`, `issues: write`, `pull-requests: write` |
| `trigger-oblt-aw-status.yml` | `actions: read`, `contents: read`, `issues: read`, `pull-requests: write` |

### Secrets

| Secret | Templates |
|--------|-----------|
| `COPILOT_GITHUB_TOKEN` | All event-scoped templates except resource-not-accessible fixer routes inside orchestrators (those use `secrets: inherit` on the route job) |
| `BUILDKITE_LOGS_API_TOKEN` → `BUILDKITE_API_TOKEN` | `trigger-oblt-aw-status.yml` only |

## Migration from per-route client templates

1. Merge distribution PRs that replace per-route `trigger-oblt-aw-*.yml` files with the three event-scoped clients above (plus unchanged schedule/status templates).
2. Distribution removes client paths that are no longer in the template tree.
3. Update Backstage `workflow_ref` / token policies to reference the new client workflow files (for example `trigger-oblt-aw-pull-request.yml` instead of separate automerge and dependency-review triggers).

## Migration from monolithic entrypoint

1. Merge distribution PRs that add event-scoped `trigger-oblt-aw-*.yml` files.
2. Delete `.github/workflows/oblt-aw.yml` and stop calling `oblt-aw-ingress` in the consumer repository. Remove any legacy per-workflow client files named `oblt-aw-*.yml` or `trg-oblt-aw-*.yml`; distribution drops paths that are no longer in the template tree.
3. Update Backstage `workflow_ref` / token policies to reference each installed **`trigger-oblt-aw-*.yml`** client workflow file.

## References

- [docs/operations/distribute-client-workflow.md](../operations/distribute-client-workflow.md)
- [aw-prelude.md](aw-prelude.md)

# Workflow: Client templates `trigger-oblt-aw-*.yml`

## Overview

**Source of truth (edit here only):** [.github/remote-workflow-template/obs/.github/workflows/](../../.github/remote-workflow-template/obs/.github/workflows/)

## Split-trigger model

Each agentic workflow has its own client template under `trigger-oblt-aw-<workflow-id>.yml` (or a descriptive suffix for multi-step features such as `trigger-oblt-aw-security-triage.yml`). Each file declares **only** the GitHub events that can trigger that workflow, then calls the matching reusable workflow in `elastic/oblt-aw`:

```yaml
uses: elastic/oblt-aw/.github/workflows/oblt-aw-<name>.yml@main
```

That removes the large number of skipped ingress jobs on unrelated events (for example issue comments no longer run automerge, dependency-review, and security jobs).

Shared dashboard gating and allow-list loading run inside each `oblt-aw-*` workflow via [aw-prelude.yml](aw-prelude.md) (first job), not in the client file.

### Architecture

```mermaid
flowchart TB
  subgraph Consumer["Consumer .github/workflows/"]
    EVT["GitHub event"]
    C_AUTO["trigger-oblt-aw-automerge.yml\non: pull_request"]
    C_TRI["trigger-oblt-aw-issue-triage.yml\non: issues"]
    C_OTHER["trigger-oblt-aw-*.yml\nother narrow on:"]
    DASH["Issue: [oblt-aw] Control Plane Dashboard"]
    EVT --> C_AUTO
    EVT --> C_TRI
    EVT -.->|on: no match| C_OTHER
  end

  subgraph OBLT["elastic/oblt-aw"]
    R["oblt-aw-* reusable"]
    PRE["aw-prelude"]
    GET["get-enabled-workflows"]
    AG["Agent steps"]
    LOCK["Upstream gh-aw lock"]
    R --> PRE --> GET
    PRE --> AG --> LOCK
  end

  DASH -.->|checkboxes| GET
  C_AUTO -->|uses: oblt-aw-automerge@main| R
  C_TRI -->|uses: oblt-aw-issue-triage@main| R
```

Full platform view (distribution, dashboard sync, before/after ingress): [architecture overview — split-trigger diagrams](../architecture/overview.md#split-trigger-vs-monolithic-ingress).

### Template index

| Client template | Triggers | Reusable workflow |
|-----------------|----------|-------------------|
| `trigger-oblt-aw-agent-suggestions.yml` | `schedule` | `oblt-aw-agent-suggestions.yml` |
| `trigger-oblt-aw-autodoc.yml` | `schedule` | `oblt-aw-autodoc.yml` |
| `trigger-oblt-aw-automerge.yml` | `pull_request` (opened, synchronize, reopened, labeled) | `oblt-aw-automerge.yml` |
| `trigger-oblt-aw-dependency-review.yml` | `pull_request` (opened, synchronize, reopened) | `oblt-aw-dependency-review.yml` |
| `trigger-oblt-aw-duplicate-issue-detector.yml` | `issues` opened, `workflow_dispatch` | `oblt-aw-duplicate-issue-detector.yml` |
| `trigger-oblt-aw-issue-triage.yml` | `issues` opened | `oblt-aw-issue-triage.yml` |
| `trigger-oblt-aw-issue-fixer.yml` | `issue_comment` created | `oblt-aw-issue-fixer.yml` |
| `trigger-oblt-aw-mention-in-issue.yml` | `issue_comment` created | `oblt-aw-mention-in-issue.yml` |
| `trigger-oblt-aw-security-detector.yml` | `schedule`, `workflow_dispatch` | `oblt-aw-security-detector.yml` |
| `trigger-oblt-aw-security-triage.yml` | `issues` opened, labeled | `oblt-aw-security-triage.yml` |
| `trigger-oblt-aw-security-fixer.yml` | `issues` labeled | `oblt-aw-security-fixer.yml` |
| `trigger-oblt-aw-resource-not-accessible-by-integration-detector.yml` | `schedule` | `oblt-aw-resource-not-accessible-by-integration-detector.yml` |
| `trigger-oblt-aw-resource-not-accessible-by-integration-triage.yml` | `issues` opened, labeled | `oblt-aw-resource-not-accessible-by-integration-triage.yml` |
| `trigger-oblt-aw-resource-not-accessible-by-integration-fixer.yml` | `issues` labeled | `oblt-aw-resource-not-accessible-by-integration-fixer.yml` |
| `trigger-oblt-aw-estc-pr-buildkite-detective.yml` | `status` (Buildkite failure only, job `if`) | `oblt-aw-estc-pr-buildkite-detective.yml` |

Route-specific conditions (labels, `/ai` comment prefix, allow-listed PR authors, and so on) are enforced inside the `oblt-aw-*` reusable workflow after [aw-prelude](aw-prelude.md) runs.

## Configuration

Top-level permissions on every client template:

- `contents: read`

Job-level permissions on `run-aw` (must stay at least as permissive as nested reusable workflows):

- `actions: write`
- `checks: read`
- `contents: write`
- `discussions: write`
- `id-token: write`
- `issues: write`
- `pull-requests: write`

### Secrets

| Secret | Templates |
|--------|-----------|
| `COPILOT_GITHUB_TOKEN` | All except `trigger-oblt-aw-issue-fixer.yml` and resource fixer (use `secrets: inherit` where noted in template) |
| `BUILDKITE_LOGS_API_TOKEN` → `BUILDKITE_API_TOKEN` | `trigger-oblt-aw-estc-pr-buildkite-detective.yml` only |

## Migration from monolithic entrypoint

1. Merge distribution PRs that add `trigger-oblt-aw-*.yml` files.
2. Delete `.github/workflows/oblt-aw.yml` and stop calling `oblt-aw-ingress` in the consumer repository. Remove any legacy per-workflow client files named `oblt-aw-*.yml` (without the `trigger-` prefix); distribution drops paths that are no longer in the template tree.
3. Update Backstage `workflow_ref` / token policies to reference each installed **`trigger-oblt-aw-*.yml`** client workflow file (one policy per workflow if your org requires narrow OIDC claims).

## References

- [docs/operations/distribute-client-workflow.md](../operations/distribute-client-workflow.md)
- [aw-prelude.md](aw-prelude.md)

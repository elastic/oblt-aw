# OBLT AW Architecture Overview

## Overview

`oblt-aw` exposes a single reusable entrypoint workflow and routes execution to specialized workflows by GitHub event context.

Entrypoint workflows:

- [.github/workflows/oblt-aw-ingress.yml](../../.github/workflows/oblt-aw-ingress.yml) (orchestration)
- [.github/workflows/get-enabled-workflows.yml](../../.github/workflows/get-enabled-workflows.yml) (dashboard read; first stage inside ingress)

Specialized workflows:

- [.github/workflows/gh-aw-dependency-review.yml](../../.github/workflows/gh-aw-dependency-review.yml)
- [.github/workflows/gh-aw-resource-not-accessible-by-integration-detector.yml](../../.github/workflows/gh-aw-resource-not-accessible-by-integration-detector.yml)
- [.github/workflows/gh-aw-resource-not-accessible-by-integration-triage.yml](../../.github/workflows/gh-aw-resource-not-accessible-by-integration-triage.yml)
- [.github/workflows/gh-aw-resource-not-accessible-by-integration-fixer.yml](../../.github/workflows/gh-aw-resource-not-accessible-by-integration-fixer.yml)

## Usage

Consumer repositories integrate once using:

```yaml
jobs:
  run-aw:
    uses: elastic/oblt-aw/.github/workflows/oblt-aw-ingress.yml@main
    secrets:
      COPILOT_GITHUB_TOKEN: ${{ secrets.COPILOT_GITHUB_TOKEN }}
```

## Control Plane Dashboard

The Control Plane Dashboard provides a self-service UI for repository users to opt in or opt out of each agentic workflow. It follows a Renovate Dependency Dashboard–style UX.

### Dashboard Issue

- **Location:** A single GitHub Issue per repository, created and maintained by the control-plane
- **Title:** `[oblt-aw] Control Plane Dashboard`
- **Label:** `oblt-aw/dashboard` (used for identification and routing)
- **Content:** Workflow list with maturity badges and checkboxes for opt-in/opt-out

### Config Flow

1. **Dashboard sync** (`sync-control-plane-dashboard`): Reads per-org `config/<org-key>/workflow-registry.json` and `active-repositories.json` (and deprecated top-level copies under `config/`); creates or updates the **single** dashboard issue in each target repository with sections per org; pins the issue when possible
2. **User edit:** Users check or uncheck workflow checkboxes in the dashboard issue (no config file; no PRs on checkbox edits)
3. **Runtime check** (`get-enabled-workflows`): When the client runs the ingress, this reusable workflow runs first. It parses the dashboard (or `effective-raw` is empty when no issue exists) and emits normalized `enabled-workflows` as a compact JSON array string (`[]` or `["id", ...]`).
4. **Ingress gating:** Routed jobs use `enabled-workflows` and `effective-raw` from `get-enabled-workflows`; empty string (no dashboard) → all workflows; empty array → none; non-empty array → only listed workflows

### Opt-in / Opt-out

- **No dashboard exists:** All workflows are activated by default
- **Dashboard exists, all unchecked:** All workflows are deactivated
- **Dashboard exists, some checked:** Only checked workflows are executed

### References

- [docs/operations/control-plane-dashboard.md](../operations/control-plane-dashboard.md) — user instructions
- [docs/operations/control-plane-dashboard-format.md](../operations/control-plane-dashboard-format.md) — dashboard issue format
- [Multi-organization agentic workflows (design)](./multi-org-agentic-workflows.md) — parameterizing registries by `config/<org-key>/` (e.g. `config/obs/`), per-org active repositories, one shared dashboard with org-grouped workflows and org-inclusive checklist markers
- [Issue #3732 comment (implementation plan)](https://github.com/elastic/observability-robots/issues/3732#issuecomment-4054356635) — canonical plan

### Issues created by agentic workflows

Any issue opened by OBLT AW workflows must use a title that starts with `[oblt-aw]`. Wrapper workflows pass a `title-prefix` (or equivalent) to upstream agentic jobs so new issues stay searchable and consistent; the dashboard issue title is `[oblt-aw] Control Plane Dashboard`.

---

## Routing Model

Current routing conditions from [.github/workflows/oblt-aw-ingress.yml](../../.github/workflows/oblt-aw-ingress.yml):

- `pull_request` + action in `opened|synchronize|reopened` + bot author in allowlist -> dependency review
- `schedule` -> resource-not-accessible detector
- `issues` + (`opened` with label `oblt-aw/detector/res-not-accessible-by-integration` OR `labeled` with that label) -> resource-not-accessible triage
- `issues` + `labeled` + required labels (`oblt-aw/ai/fix-ready` and `oblt-aw/triage/res-not-accessible-by-integration`) -> resource-not-accessible fixer
- unsupported event/action combinations -> `unsupported-trigger` fail-fast job

*Note: Dashboard opt-in/opt-out is read at runtime inside the ingress via `get-enabled-workflows`; there is no `issues.edited` trigger.*

## Examples

```mermaid
flowchart TD
  A[Consumer Repository] --> C[oblt-aw-ingress]
  C --> B[get-enabled-workflows]
  C --> D[Dependency Review]
  C --> E[Resource Not Accessible by Integration Detector]
  C --> F[Resource Not Accessible by Integration Triage]
  C --> G[Resource Not Accessible by Integration Fixer]
  C --> X[Unsupported Trigger]
```

*The ingress calls `get-enabled-workflows` first to read the dashboard issue; each routed job is gated by the effective `enabled-workflows` value.*

## References

- [docs/workflows/README.md](../workflows/README.md)
- [docs/routing/README.md](../routing/README.md)

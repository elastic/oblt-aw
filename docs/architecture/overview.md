# OBLT AW Architecture Overview

## Overview

`oblt-aw` exposes a single reusable entrypoint workflow and routes execution to specialized workflows by GitHub event context.

Entrypoint workflow:

- `.github/workflows/oblt-aw-ingress.yml`

Specialized workflows:

- `.github/workflows/gh-aw-dependency-review.yml`
- `.github/workflows/gh-aw-resource-not-accessible-by-integration-detector.yml`
- `.github/workflows/gh-aw-resource-not-accessible-by-integration-triage.yml`
- `.github/workflows/gh-aw-resource-not-accessible-by-integration-fixer.yml`

## Usage

Consumer repositories integrate once using:

```yaml
jobs:
  run-aw:
    uses: elastic/oblt-aw/.github/workflows/oblt-aw-ingress.yml@main
```

## Control Plane Dashboard

The Control Plane Dashboard provides a self-service UI for repository users to opt in or opt out of each agentic workflow. It follows a Renovate Dependency Dashboard–style UX.

### Dashboard Issue

- **Location:** A single GitHub Issue per repository, created and maintained by the control-plane
- **Title:** `[oblt-aw] Control Plane Dashboard`
- **Label:** `oblt-aw/dashboard` (used for identification and routing)
- **Content:** Workflow list with maturity badges and checkboxes for opt-in/opt-out

### Config Flow

1. **Dashboard sync** (`sync-control-plane-dashboard`): Reads `workflow-registry.json` and `active-repositories.json`; creates or updates the dashboard issue in each target repository; pins the issue when possible
2. **User edit:** Users check or uncheck workflow checkboxes in the dashboard issue (no config file; no PRs on checkbox edits)
3. **Runtime check** (`check-dashboard`): When the client runs, a `check-dashboard` job runs **before** calling the ingress. If no open dashboard issue exists, it outputs an empty string for `enabled_workflows`. Otherwise it fetches the issue via API, parses checkboxes (`^- [x] <!-- oblt-aw:workflow-id -->` at line start in the Enable/Disable list), and outputs `enabled_workflows` as a JSON array string (`[]` or `["id", ...]`).
4. **Ingress gating:** The ingress receives `enabled_workflows` as input from the client; empty string (no dashboard) → all workflows; empty array → none; non-empty array → only listed workflows

### Opt-in / Opt-out

- **No dashboard exists:** All workflows are activated by default
- **Dashboard exists, all unchecked:** All workflows are deactivated
- **Dashboard exists, some checked:** Only checked workflows are executed

### References

- `docs/operations/control-plane-dashboard.md` — user instructions
- `docs/operations/control-plane-dashboard-format.md` — dashboard issue format
- [Issue #3732 comment (implementation plan)](https://github.com/elastic/observability-robots/issues/3732#issuecomment-4054356635) — canonical plan

### Issues created by agentic workflows

Any issue opened by OBLT AW workflows must use a title that starts with `[oblt-aw]`. Wrapper workflows pass a `title-prefix` (or equivalent) to upstream agentic jobs so new issues stay searchable and consistent; the dashboard issue title is `[oblt-aw] Control Plane Dashboard`.

---

## Routing Model

Current routing conditions from `.github/workflows/oblt-aw-ingress.yml`:

- `pull_request` + action in `opened|synchronize|reopened` + bot author in allowlist -> dependency review
- `schedule` -> resource-not-accessible detector
- `issues` + (`opened` with label `oblt-aw/detector/res-not-accessible-by-integration` OR `labeled` with that label) -> resource-not-accessible triage
- `issues` + `labeled` + required labels (`oblt-aw/ai/fix-ready` and `oblt-aw/triage/res-not-accessible-by-integration`) -> resource-not-accessible fixer
- unsupported event/action combinations -> `unsupported-trigger` fail-fast job

*Note: Dashboard opt-in/opt-out is read at runtime by the client's `check-dashboard` job before calling the ingress; there is no `issues.edited` trigger.*

## Examples

```mermaid
flowchart TD
  A[Consumer Repository] --> B[check-dashboard]
  B --> C[oblt-aw-ingress]
  C --> D[Dependency Review]
  C --> E[Resource Not Accessible by Integration Detector]
  C --> F[Resource Not Accessible by Integration Triage]
  C --> G[Resource Not Accessible by Integration Fixer]
  C --> X[Unsupported Trigger]
```

*The client runs `check-dashboard` first to read the dashboard issue and pass `enabled_workflows` to the ingress; each workflow job is gated by that input.*

## References

- `docs/workflows/README.md`
- `docs/routing/README.md`

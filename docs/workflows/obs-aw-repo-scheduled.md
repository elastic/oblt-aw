# Workflow: `obs-aw-repo-scheduled.yml`

## Overview

Source file: [.github/workflows/obs-aw-repo-scheduled.yml](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/obs-aw-repo-scheduled.yml)

Generic scheduled agentic workflow for **consumer-defined** automations. The framework owns compilation, the lock file, schedule lanes, and capability wiring. Consumers declare automations in `apm.yml`, point each entry at an instruction Markdown file, and enable the Control Plane dashboard checkbox `obs:repo-scheduled`.

## Prerequisites

- Repository registered and schedule clients installed ([Onboard a repository](../user-guide/onboard-a-repository.md)).
- Control Plane dashboard checkbox **Repo Scheduled** enabled ([Enable or disable an agentic workflow](../user-guide/enable-a-new-workflow.md)).
- At least one entry under `x-oblt-aw.obs.workflows.repo-scheduled.automations` whose `schedule-profiles` includes the wake lane.
- For `capabilities: [buildkite-logs]`: repository secret `BUILDKITE_LOGS_API_TOKEN` (same name as the status detective).

## Consumer declaration (`apm.yml`)

Declare automations under the Observability workflow block. Each entry requires `instructions-file`. Set `schedule-profiles` (and optional `id` / `capabilities`) on the APM entry and/or in the instruction file frontmatter. When both set a field, the APM value wins.

```yaml
x-oblt-aw:
  version: 1
  obs:
    common: {}
    workflows:
      repo-scheduled:
        automations:
          - id: build-error-triage
            instructions-file: docs/ai/build-error-triage.md
            schedule-profiles: [weekly]
            capabilities: [buildkite-logs]
```

Instruction file (body is required; frontmatter is optional when profiles live in APM):

```markdown
---
# Optional when schedule-profiles / capabilities / id are set in apm.yml
schedule-profiles: [weekly]
capabilities:
  - buildkite-logs
---

Detect Buildkite build errors over the last 7 days…
```

| Field | Where | Required | Meaning |
|-------|-------|----------|---------|
| `instructions-file` | APM only | yes | Repo-relative path to the Markdown body |
| `schedule-profiles` | APM and/or frontmatter | yes (one place) | One or more of `daily`, `frequent`, `weekly` |
| `capabilities` | APM and/or frontmatter | no | Allowlisted ids (today: `buildkite-logs`) |
| `id` | APM and/or frontmatter | no | Defaults to the instruction file stem |

Do **not** add consumer cron workflows, GH-AW sources, or lock files for this feature. Discovery does not glob a fixed directory; only APM-listed paths run.

## Schedule lanes

| Profile | Client trigger | Typical cron |
|---------|----------------|--------------|
| `daily` | `trigger-obs-aw-schedule-daily.yml` | `0 6 * * *` |
| `frequent` | `trigger-obs-aw-schedule-frequent.yml` | `*/15 * * * *` |
| `weekly` | `trigger-obs-aw-schedule-weekly.yml` | `0 6 * * 1` (Monday) |

On each wake, discovery keeps only automations whose effective `schedule-profiles` include that profile.

## Capabilities

| Id | Secret (consumer name) | Framework wiring |
|----|------------------------|------------------|
| `buildkite-logs` | `BUILDKITE_LOGS_API_TOKEN` → `BUILDKITE_API_TOKEN` | Buildkite MCP in `gh-aw-repo-scheduled` |

Secrets are **optional** on the schedule call chain. If an automation lists a capability and the secret is missing, discovery fails closed for that wake.

## Ownership

| Concern | Owner |
|---------|--------|
| Control Plane enablement | Dashboard checkbox `obs:repo-scheduled` |
| Cron / lanes | Framework client templates |
| MCP / secret maps for allowlisted capabilities | Framework |
| Which files run | Consumer `apm.yml` automations list |
| What the agent does | Consumer instruction files |

## Safe outputs and permissions

Non-destructive safe-outputs on the generic AW: `create-issue`, `add-comment`, `add-labels`, plus system `noop` / `missing-*` / `report-incomplete` (issue creation off for those). Job permissions stay read-heavy with `issues: write` and `pull-requests: write` for comments/labels; no `contents: write`.

## Migration notes (golang-crossbuild-style AWs)

1. Enable **Repo Scheduled** on the Control Plane dashboard.
2. Add an `apm.yml` automation with `instructions-file`, `schedule-profiles: [weekly]`, and `capabilities: [buildkite-logs]`; move prompt/skill text into the instruction body.
3. Keep provisioning `BUILDKITE_LOGS_API_TOKEN`.
4. Remove the consumer-owned `debug-build-report.md` / lock / local cron once the framework path is verified.

## References

- Routing: [docs/routing/repo-scheduled-routing.md](../routing/repo-scheduled-routing.md)
- Schedule orchestrator: [obs-aw-event-schedule.md](obs-aw-event-schedule.md)
- Client templates: [obs-aw-client-template.md](obs-aw-client-template.md)
- Issue: [#2197](https://github.com/elastic/oblt-aw/issues/2197)

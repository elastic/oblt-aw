# Run your own scheduled automations

## Overview

Use **Repo Scheduled** (`obs:repo-scheduled`) when you want a cron-driven agent in your repository, but you do not want to own GH-AW compilation, lock files, or schedule client YAML.

You write the automation as instruction Markdown (and optional allowlisted capabilities). `oblt-aw` owns the generic agentic workflow, schedule lanes (`daily` / `frequent` / `weekly`), dashboard gating, and capability wiring such as Buildkite logs.

This guide is the user journey. Contract detail lives in [Repo Scheduled](../workflows/obs-aw-repo-scheduled.md) ([#2197](https://github.com/elastic/oblt-aw/issues/2197)).

```mermaid
flowchart TD
  A[Enable obs:repo-scheduled on Control Plane dashboard] --> B[Commit apm.yml automations]
  B --> C[Add instruction Markdown or inline instructions]
  C --> D[Optional: secrets for allowlisted capabilities]
  D --> E[Wait for matching schedule lane]
  E --> F{Discovery finds automation for this lane?}
  F -->|no| Z[Route skips / no agent leaf]
  F -->|yes| G[Agent runs with your instructions]
  G --> H[Safe outputs: issue / comment / labels]
```

## Prerequisites

- The repository is registered and Observability schedule clients are installed (`trigger-obs-aw-schedule-daily.yml`, `trigger-obs-aw-schedule-frequent.yml`, `trigger-obs-aw-schedule-weekly.yml`). See [Onboard a repository](onboard-a-repository.md).
- **Repo Scheduled** (`obs:repo-scheduled`) is checked on the Control Plane dashboard. See [Enable or disable an agentic workflow](enable-a-new-workflow.md).
- You know which lane you need: `daily`, `frequent`, or `weekly` (see [Schedule lanes](#schedule-lanes)).

## Who owns what

| Concern | Owner |
|---------|--------|
| Dashboard enablement (`obs:repo-scheduled`) | You (checkbox) |
| Cron clients and lanes | Framework |
| Lock file / AW compilation | Framework |
| Which automations run | Your `apm.yml` `automations` list |
| What the agent does | Your instruction files or inline `instructions` |
| Optional Buildkite MCP (`buildkite-logs`) | Framework wiring + your `BUILDKITE_LOGS_API_TOKEN` secret |

## User journeys

### First weekly automation (happy path)

Goal: one scheduled agent that creates an issue or comments when your instructions say so.

1. **Add root `apm.yml`** — Declare at least one automation under `x-oblt-aw.obs.workflows.repo-scheduled.automations`. Prefer an `instructions-file` under `.github/oblt-aw/scheduled/`. Every org block still needs `common` (it can be empty `{}`).

```yaml
x-oblt-aw:
  version: 1
  obs:
    common: {}
    workflows:
      repo-scheduled:
        automations:
          - id: weekly-nudge
            instructions-file: .github/oblt-aw/scheduled/weekly-nudge.md
            schedule-profiles: [weekly]
```

2. **Write the instruction file** — Put the agent brief in the Markdown body. Frontmatter is optional when `schedule-profiles` (and optional `id` / `capabilities`) are already set in `apm.yml`.

```markdown
---
schedule-profiles: [weekly]
---

Scan open pull requests idle for more than 14 days.
Add a short comment that asks for an update or a close decision.
Do not change repository files.
```

3. **Merge to the default branch** — Discovery reads the consumer checkout for that schedule run.

4. **Wait for the weekly lane** — `trigger-obs-aw-schedule-weekly.yml` (typical cron `0 6 * * 1` UTC). Or ask a maintainer to dispatch the schedule client with the weekly profile when your repo allows `workflow_dispatch`.

5. **Confirm in Actions** — Open the schedule client run in your repository. Expect prelude gating for `obs:repo-scheduled`, a discover step that lists your automation id, then an agent leaf for that id. Safe outputs are non-destructive (`create-issue`, `add-comment`, `add-labels`); there is no `contents: write`.

### Buildkite build-error triage (capability + secret)

Goal: weekly triage of Buildkite failures, same pattern as consumer-owned AWs such as golang-crossbuild’s debug-build report, without a local lock file.

1. Complete the [first weekly automation](#first-weekly-automation-happy-path) steps with `schedule-profiles: [weekly]` and `capabilities: [buildkite-logs]`.

```yaml
repo-scheduled:
  automations:
    - id: build-error-triage
      instructions-file: .github/oblt-aw/scheduled/build-error-triage.md
      schedule-profiles: [weekly]
      capabilities: [buildkite-logs]
```

2. **Add the repository secret** `BUILDKITE_LOGS_API_TOKEN` (same name as the status detective). The framework maps it to Buildkite MCP. See [Configure a GitHub secret](../admin-guide/configure-a-github-secret.md).

3. **Put triage guidance in the instruction body** — pipeline slug, lookback window, how to categorize failures, issue title/body conventions, labels such as `observablt-ci`, and when to open or skip an issue.

4. **If discovery fails closed** — An automation that lists `buildkite-logs` without the secret present fails that wake. Fix the secret, then wait for the next weekly run.

Copy-paste example: [consumer-apm.yml.example](https://raw.githubusercontent.com/elastic/oblt-aw/main/docs/examples/consumer-apm.yml.example). Full field table: [Repo Scheduled](../workflows/obs-aw-repo-scheduled.md).

### Nothing should run (fail-closed paths)

Use these checks when you expect silence:

| Situation | Expected result |
|-----------|-----------------|
| **Repo Scheduled** unchecked (or no dashboard) | Schedule route does not proceed for `obs:repo-scheduled` |
| No `automations` entry, or none whose `schedule-profiles` include the wake lane | Discovery finds no work; no agent leaf for your automation |
| `buildkite-logs` listed but `BUILDKITE_LOGS_API_TOKEN` missing | Discovery fails closed for that wake |
| Instruction only on a feature branch, schedule checks out default | Automation not seen until merged (or until the run uses that ref) |

Uncheck the dashboard box to stop all consumer-defined scheduled automations for the repository. To pause one automation only, **remove that entire entry** from `x-oblt-aw.obs.workflows.repo-scheduled.automations` in `apm.yml`. Clearing or retargeting `schedule-profiles` alone is not enough when the same profiles still exist in the instruction frontmatter (or when you only switch to another lane you still want to avoid).

### Migrate off a consumer-owned scheduled AW

If the repository already runs a local GH-AW (source `.md`, generated `.lock.yml`, compiler pin, and its own `schedule` trigger):

1. Enable **Repo Scheduled** and add an `apm.yml` automation that points at your prompt text (move it under `.github/oblt-aw/scheduled/` or use inline `instructions` with an `id`).
2. Keep the same lane and secrets (for Buildkite triage: `weekly` + `BUILDKITE_LOGS_API_TOKEN`).
3. Prove one green framework path (schedule or `workflow_dispatch`).
4. Remove the consumer lock, local cron workflow, and compile-check plumbing for that AW so you do not double-run.

## Schedule lanes

| Profile | Client trigger | Typical cron (UTC) | Use when |
|---------|----------------|--------------------|----------|
| `daily` | `trigger-obs-aw-schedule-daily.yml` | `0 6 * * *` | Once-per-day audits or summaries |
| `frequent` | `trigger-obs-aw-schedule-frequent.yml` | `*/15 * * * *` | Short-interval checks (use sparingly) |
| `weekly` | `trigger-obs-aw-schedule-weekly.yml` | `0 6 * * 1` | Weekly triage (for example build-error reports) |

List one or more profiles per automation. On each wake, only automations whose effective profiles include that lane run.

## Instructions and capabilities

Repo Scheduled still calls [resolve agentic assets](../workflows/aw-resolve-agentic-assets.md) before the agent leaf. For this route:

- Put the full agent brief in the instruction Markdown or inline `instructions` (this is what the scheduled agent receives).
- Use allowlisted `capabilities` (today: `buildkite-logs`) when you need framework-wired tools and secrets.
- Use `obs.common` / other `workflows.<id>` blocks for shared setup or instructions on **other** agentic workflows; `workflows.repo-scheduled` is the override block for this route and holds the `automations` list.

Do **not** rely on top-level `dependencies.apm` for Repo Scheduled behavior. That install runs in the resolve job; the scheduled agent gets the resolved instruction text, not the installed package files or MCP config from those packages. For skills-style guidance on this route, put it in the instruction body. Broader APM package use on other workflows: [Define local AI assets](local-ai-assets.md).

## Example use cases (instruction content)

These are examples of what you put in the instruction body. The framework does not ship separate routes per use case; one generic AW runs whatever you declare.

| Use case | Typical lane | Typical capability |
|----------|--------------|--------------------|
| Buildkite build-error detect and triage | `weekly` | `buildkite-logs` |
| Build execution summary over a lookback window | `daily` or `weekly` | `buildkite-logs` when logs are required |
| Flaky-test detection notes or issue filing | `daily` or `weekly` | none, unless you need Buildkite MCP |

## What not to do

- Do **not** add consumer cron workflows, GH-AW sources, or lock files for Repo Scheduled.
- Do **not** rely on directory globbing; only automations listed under `x-oblt-aw.obs.workflows.repo-scheduled.automations` run.
- Do **not** expect `contents: write` or PR creation from this generic AW’s safe outputs.

## References

- [Repo Scheduled workflow](../workflows/obs-aw-repo-scheduled.md) — fields, capabilities, ownership, migration notes
- [Repo Scheduled routing](../routing/repo-scheduled-routing.md) — client → orchestrator → route gates
- [Define local AI assets](local-ai-assets.md) — `apm.yml` for other consumer customizations
- [Enable or disable an agentic workflow](enable-a-new-workflow.md) — Control Plane dashboard
- [Example consumer `apm.yml`](https://raw.githubusercontent.com/elastic/oblt-aw/main/docs/examples/consumer-apm.yml.example)
- Feature: [#2197](https://github.com/elastic/oblt-aw/issues/2197)

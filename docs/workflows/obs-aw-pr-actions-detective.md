# Workflow: `obs-aw-pr-actions-detective.yml`

## Overview

Source file: [.github/workflows/obs-aw-pr-actions-detective.yml](../../.github/workflows/obs-aw-pr-actions-detective.yml)

Reusable wrapper that calls the upstream PR Actions Detective lock. Client `trigger-obs-aw-workflow-run.yml` routes failed GitHub Actions `workflow_run` events here when prelude allows `obs:pr-actions-detective`.

## Prerequisites

- Triggered via `workflow_call` from the workflow-run event orchestrator (`obs-aw-event-workflow-run.yml` ← client `trigger-obs-aw-workflow-run.yml`).
- No consumer secrets beyond the usual agentic token setup (no Buildkite token).
- The client trigger is installed only when `pr-actions-detective-workflows` is non-empty in [active-repositories.json](../../config/obs/active-repositories.json). Distribute renders those workflow **`name:`** values into `on.workflow_run.workflows`. The job `if` keeps only failures with associated pull requests. Dashboard gating (`obs:pr-actions-detective`) remains off by default.

## Usage

Ingress routes here when:

- the consumer has a non-empty `pr-actions-detective-workflows` allowlist and the distributed trigger is present,
- `github.event_name == 'workflow_run'` for one of those named workflows,
- `github.event.workflow_run.conclusion == 'failure'`,
- the completed run has a non-empty associated pull-request list, and
- Dashboard gate passes for registry id `pr-actions-detective` (`enabled-workflows` contains `obs:pr-actions-detective`).

The job `pr-actions-detective` calls:

```yaml
uses: elastic/ai-github-actions/.github/workflows/gh-aw-pr-actions-detective.lock.yml@main
```

### Opinionated vs preserved

| Opinionated (Observability-owned) | Preserved as lock inputs |
|-----------------------------------|--------------------------|
| `report-failure-as-issue: false` (no meta-issue on agent failure) | `additional-instructions` (from `aw-resolve-agentic-assets`) |
| Wrapper exposes only `shared-proceed` | `setup-commands` (joined from consumer `apm.yml` when non-empty) |

## Configuration

Permissions on the agent job:

- `actions: read`
- `contents: read`
- `issues: write`
- `pull-requests: write`
- `copilot-requests: write`

## API / Interface

Wrapper `workflow_call` contract:

- Input: `shared-proceed` (`required: true`)

Lock inputs passed by the wrapper:

- `additional-instructions` — resolved control-plane + consumer instructions
- `setup-commands` — `join(fromJSON(resolved-setup-commands-json), fromJSON('"\n"'))` from resolve (empty when the consumer has none)
- `report-failure-as-issue: false`

## References

- Client template: [obs-aw-client-template.md](obs-aw-client-template.md) — registry id `pr-actions-detective`
- Upstream lock: [elastic/ai-github-actions](https://github.com/elastic/ai-github-actions) — [`.github/workflows/gh-aw-pr-actions-detective.lock.yml`](https://github.com/elastic/ai-github-actions/blob/main/.github/workflows/gh-aw-pr-actions-detective.lock.yml)
- Upstream documentation: [elastic.github.io/ai-github-actions](https://elastic.github.io/ai-github-actions/workflows/gh-agent-workflows/pr-actions-detective/)

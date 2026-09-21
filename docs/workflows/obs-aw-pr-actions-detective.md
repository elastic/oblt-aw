# Workflow: `obs-aw-pr-actions-detective.yml`

## Overview

Source file: [.github/workflows/obs-aw-pr-actions-detective.yml](../../.github/workflows/obs-aw-pr-actions-detective.yml)

Reusable wrapper that calls the Observability-owned PR Actions Detective lock in this repository. Client `trigger-obs-aw-workflow-run.yml` routes failed GitHub Actions `workflow_run` events here when prelude allows `obs:pr-actions-detective`.

Landing home for this primitive (under [#2055](https://github.com/elastic/oblt-aw/issues/2055) / [#1876](https://github.com/elastic/oblt-aw/issues/1876)): **`elastic/oblt-aw`**.

## Prerequisites

- Triggered via `workflow_call` from the workflow-run event orchestrator (`obs-aw-event-workflow-run.yml` ← client `trigger-obs-aw-workflow-run.yml`).
- No consumer secrets beyond the usual agentic token setup (no Buildkite token).
- The client template listens for all completed `workflow_run` events; the job `if` keeps only failures with associated pull requests. Dashboard gating (`obs:pr-actions-detective`) remains off by default.

## Usage

Ingress routes here when:

- `github.event_name == 'workflow_run'`,
- `github.event.workflow_run.conclusion == 'failure'`,
- the completed run has a non-empty associated pull-request list, and
- Dashboard gate passes for registry id `pr-actions-detective` (`enabled-workflows` contains `obs:pr-actions-detective`).

The job `pr-actions-detective` calls:

```yaml
uses: elastic/oblt-aw/.github/workflows/gh-aw-pr-actions-detective.lock.yml@main
```

Edit the GH-AW source [`.github/workflows/gh-aw-pr-actions-detective.md`](../../.github/workflows/gh-aw-pr-actions-detective.md) and compile with `make compile-aw-check` from the repository root (do not hand-edit the lock).

### Opinionated vs preserved

| Opinionated (Observability-owned) | Preserved as lock inputs |
|-----------------------------------|--------------------------|
| Model, failure-issue suppression (`report-failure-as-issue` / `report-failed-jobs` false; `noop` / `missing-tool` / `missing-data` / `report-incomplete` do not create issues), and GitHub `trusted-users` via [`.github/workflows/gh-aw-fragments/obs-defaults.md`](../../.github/workflows/gh-aw-fragments/obs-defaults.md) | `additional-instructions` (from `aw-resolve-agentic-assets`) |
| Comment footer via [`.github/workflows/gh-aw-fragments/messages-footer.md`](../../.github/workflows/gh-aw-fragments/messages-footer.md) (What is this? → [oblt-aw README](https://github.com/elastic/oblt-aw/blob/main/README.md)) | `setup-commands` (joined from consumer `apm.yml` when non-empty) |
| Bot actors hardcoded on the source (`github-actions[bot]`) — GH-AW does not allow `on.bots` in shared fragments | |
| Wrapper exposes only `shared-proceed` | |

Shared compile imports for this workflow also include the other files under [`.github/workflows/gh-aw-fragments/`](../../.github/workflows/gh-aw-fragments/) (including `mcp-pagination.md`).

## Configuration

Permissions on the agent job:

- `actions: read`
- `contents: read`
- `issues: write`
- `pull-requests: write`
- `copilot-requests: write`

Conclusion and safe-outputs jobs request `pull-requests: write` only where needed; failure fallbacks do not create tracking issues (`obs-defaults`).

## API / Interface

Wrapper `workflow_call` contract:

- Input: `shared-proceed` (`required: true`)

Lock inputs passed by the wrapper:

- `additional-instructions` — resolved control-plane + consumer instructions
- `setup-commands` — `join(fromJSON(resolved-setup-commands-json), fromJSON('"\n"'))` from resolve (empty when the consumer has none; `fromJSON` supplies a real newline because expression string literals do not interpret `\n`)

## Cutover and rollback

**Cutover:** the wrapper `uses` `elastic/oblt-aw/.../gh-aw-pr-actions-detective.lock.yml@main` instead of `elastic/ai-github-actions/...@main`. Consumer event routing is unchanged.

**Rollback:** point the wrapper job back at the previous upstream lock:

```yaml
uses: elastic/ai-github-actions/.github/workflows/gh-aw-pr-actions-detective.lock.yml@main
```

When rolling back, restore wrapper `with.report-failure-as-issue: false` if the upstream lock still defaults that input to `true`.

Copies in `elastic/ai-github-actions` remain for other consumers; this migration does not deprecate or remove them.

**Integration (no live model):** fixtures and wiring checks for resolve → wrapper → lock inputs live under [`testdata/agentic/pr-actions-detective/`](../../testdata/agentic/pr-actions-detective/) and [`tests/integration/test_pr_actions_detective.py`](../../tests/integration/test_pr_actions_detective.py) ([#2055](https://github.com/elastic/oblt-aw/issues/2055)).

**E2E / production workflow_run validation:** deferred (sibling of [#1911](https://github.com/elastic/oblt-aw/issues/1911) / testing platform [#1877](https://github.com/elastic/oblt-aw/issues/1877)).

## References

- Client template: [obs-aw-client-template.md](obs-aw-client-template.md) — registry id `pr-actions-detective`
- In-repo source: [`.github/workflows/gh-aw-pr-actions-detective.md`](../../.github/workflows/gh-aw-pr-actions-detective.md)
- In-repo lock: [`.github/workflows/gh-aw-pr-actions-detective.lock.yml`](../../.github/workflows/gh-aw-pr-actions-detective.lock.yml)
- Shared model defaults: [`.github/workflows/gh-aw-fragments/obs-defaults.md`](../../.github/workflows/gh-aw-fragments/obs-defaults.md)
- Prior upstream (rollback / other consumers): [elastic/ai-github-actions](https://github.com/elastic/ai-github-actions) — [`.github/workflows/gh-aw-pr-actions-detective.lock.yml`](https://github.com/elastic/ai-github-actions/blob/main/.github/workflows/gh-aw-pr-actions-detective.lock.yml)
- Prior upstream documentation: [elastic.github.io/ai-github-actions](https://elastic.github.io/ai-github-actions/workflows/gh-agent-workflows/pr-actions-detective/)
- Ingress: [#2054](https://github.com/elastic/oblt-aw/pull/2054) / product [#1556](https://github.com/elastic/oblt-aw/issues/1556)

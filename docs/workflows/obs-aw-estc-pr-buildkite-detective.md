# Workflow: `obs-aw-estc-pr-buildkite-detective.yml`

## Overview

Source file: [.github/workflows/obs-aw-estc-pr-buildkite-detective.yml](../../.github/workflows/obs-aw-estc-pr-buildkite-detective.yml)

Reusable wrapper that calls the Observability-owned PR Buildkite Detective lock in this repository. Client `trigger-obs-aw-status.yml` routes failed Buildkite `status` events here when prelude allows `obs:estc-pr-buildkite-detective`.

Landing home for this primitive (pilot under [#1882](https://github.com/elastic/oblt-aw/issues/1882) / [#1876](https://github.com/elastic/oblt-aw/issues/1876)): **`elastic/oblt-aw`**.

## Prerequisites

- Triggered via `workflow_call` from the status event orchestrator (`obs-aw-event-status.yml` ← client `trigger-obs-aw-status.yml`).
- Required secret: `BUILDKITE_API_TOKEN` — a Buildkite API token with read access to build logs for the repository's Buildkite organization. In consumer repositories, map this from `BUILDKITE_LOGS_API_TOKEN`.
- Optional secret: `GH_AW_DEFAULT_OTLP_HEADERS` — when configured in a consumer repository, this wrapper forwards the secret to the in-repo GH-AW lock, which already includes the runtime OpenTelemetry export wiring for the shared `GH_AW_DEFAULT_OTLP_ENDPOINT` variable.

## Usage

Ingress routes here when:

- `github.event_name == 'status'`,
- `github.event.state == 'failure'`, and
- `github.event.context` contains `buildkite`, and
- Dashboard gate passes for registry id `estc-pr-buildkite-detective` (`enabled-workflows` contains `obs:estc-pr-buildkite-detective`).

The job `estc-pr-buildkite-detective` calls:

```yaml
uses: elastic/oblt-aw/.github/workflows/gh-aw-estc-pr-buildkite-detective.lock.yml@main
```

Edit the GH-AW source [`.github/workflows/gh-aw-estc-pr-buildkite-detective.md`](../../.github/workflows/gh-aw-estc-pr-buildkite-detective.md) and compile with `gh aw compile gh-aw-estc-pr-buildkite-detective` (do not hand-edit the lock).

### Opinionated vs preserved

| Opinionated (Observability-owned) | Preserved as lock inputs |
|-----------------------------------|--------------------------|
| Model, failure-issue suppression (`report-failure-as-issue` / `report-failed-jobs` false; `noop` / `missing-tool` / `missing-data` / `report-incomplete` do not create issues), and GitHub `trusted-users` via [`.github/workflows/gh-aw-fragments/obs-defaults.md`](../../.github/workflows/gh-aw-fragments/obs-defaults.md) | `additional-instructions` (from `aw-resolve-agentic-assets`) |
| Comment footer via [`.github/workflows/gh-aw-fragments/messages-footer.md`](../../.github/workflows/gh-aw-fragments/messages-footer.md) (What is this? → [oblt-aw README](https://github.com/elastic/oblt-aw/blob/main/README.md)) | `setup-commands` (joined from consumer `apm.yml` when non-empty) |
| Bot actors hardcoded on the source (`github-actions[bot]`, `buildkite-limited-access[bot]`) — GH-AW does not allow `on.bots` in shared fragments | |
| Wrapper exposes `shared-proceed`, the required Buildkite secret, and the optional OTLP headers secret | |

Shared compile imports for this workflow also include the other files under [`.github/workflows/gh-aw-fragments/`](../../.github/workflows/gh-aw-fragments/).

## Configuration

Permissions on the agent job:

- `actions: read`
- `contents: read`
- `issues: read`
- `pull-requests: read`
- `copilot-requests: write`

Conclusion and safe-outputs jobs request `pull-requests: write` only (no `issues: write`); failure fallbacks do not create tracking issues.

## API / Interface

Wrapper `workflow_call` contract:

- Input: `shared-proceed` (`required: true`)
- Secret: `BUILDKITE_API_TOKEN` (`required: true`)
- Secret: `GH_AW_DEFAULT_OTLP_HEADERS` (`required: false`)

Lock inputs passed by the wrapper:

- `additional-instructions` — resolved control-plane + consumer instructions
- `setup-commands` — `join(fromJSON(resolved-setup-commands-json), '\n')` from resolve (empty when the consumer has none)

Lock secrets forwarded by the wrapper:

- `BUILDKITE_API_TOKEN`
- `GH_AW_DEFAULT_OTLP_HEADERS` (optional)

Migration note for consumers: if you previously configured the consumer-facing secret name as `BUILDKITE_API_TOKEN`, rename or duplicate it as `BUILDKITE_LOGS_API_TOKEN` in repository/organization secrets.

## Cutover and rollback

**Cutover (this pilot):** the wrapper `uses` `elastic/oblt-aw/.../gh-aw-estc-pr-buildkite-detective.lock.yml@main` instead of `elastic/ai-github-actions/...@main`. Existing Buildkite secret mapping and event routing are unchanged, and consumers may now also forward `GH_AW_DEFAULT_OTLP_HEADERS` when telemetry headers are needed.

**Rollback:** point the wrapper job back at the previous upstream lock:

```yaml
uses: elastic/ai-github-actions/.github/workflows/gh-aw-estc-pr-buildkite-detective.lock.yml@main
```

Copies in `elastic/ai-github-actions` remain for other consumers; this pilot does not deprecate or remove them.

**E2E / production-like status-path validation:** not covered here. Tracked under [#1877](https://github.com/elastic/oblt-aw/issues/1877).

## References

- Client template: [obs-aw-client-template.md](obs-aw-client-template.md) — registry id `estc-pr-buildkite-detective`
- In-repo source: [`.github/workflows/gh-aw-estc-pr-buildkite-detective.md`](../../.github/workflows/gh-aw-estc-pr-buildkite-detective.md)
- In-repo lock: [`.github/workflows/gh-aw-estc-pr-buildkite-detective.lock.yml`](../../.github/workflows/gh-aw-estc-pr-buildkite-detective.lock.yml)
- Shared model defaults: [`.github/workflows/gh-aw-fragments/obs-defaults.md`](../../.github/workflows/gh-aw-fragments/obs-defaults.md)
- Prior upstream (rollback / other consumers): [elastic/ai-github-actions](https://github.com/elastic/ai-github-actions) — [`.github/workflows/gh-aw-estc-pr-buildkite-detective.lock.yml`](https://github.com/elastic/ai-github-actions/blob/main/.github/workflows/gh-aw-estc-pr-buildkite-detective.lock.yml)
- Prior upstream documentation: [elastic.github.io/ai-github-actions](https://elastic.github.io/ai-github-actions/workflows/gh-agent-workflows/estc-pr-buildkite-detective/)

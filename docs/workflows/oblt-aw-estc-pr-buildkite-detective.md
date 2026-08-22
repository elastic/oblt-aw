# Workflow: `oblt-aw-estc-pr-buildkite-detective.yml`

## Overview

Source file: [.github/workflows/oblt-aw-estc-pr-buildkite-detective.yml](../../.github/workflows/oblt-aw-estc-pr-buildkite-detective.yml)

Reusable wrapper that calls the locked PR Buildkite Detective workflow in [elastic/ai-github-actions](https://github.com/elastic/ai-github-actions). The status client template `trigger-oblt-aw-status.yml` calls `oblt-aw-event-status.yml`, which fans out to this route on failed Buildkite `status` events when prelude allows `obs:estc-pr-buildkite-detective`.

## Prerequisites

- Triggered via `workflow_call` from `oblt-aw-event-status.yml` (invoked by `trigger-oblt-aw-status.yml` in client repositories).
- Required secret: `BUILDKITE_API_TOKEN` — a Buildkite API token with read access to build logs for the repository's Buildkite organization. In consumer repositories, map this from `BUILDKITE_LOGS_API_TOKEN`.

## Usage

Ingress routes here when:

- `github.event_name == 'status'`,
- `github.event.state == 'failure'`, and
- `github.event.context` contains `buildkite`, and
- Dashboard gate passes for registry id `estc-pr-buildkite-detective` (`enabled-workflows` contains `obs:estc-pr-buildkite-detective`).

The job `estc-pr-buildkite-detective` calls:

- [elastic/ai-github-actions/.github/workflows/gh-aw-estc-pr-buildkite-detective.lock.yml@main](https://github.com/elastic/ai-github-actions/blob/main/.github/workflows/gh-aw-estc-pr-buildkite-detective.lock.yml)

Behavior and agent instructions for the locked workflow are defined in [elastic/ai-github-actions](https://github.com/elastic/ai-github-actions).

## Configuration

Permissions:

- `actions: read`
- `contents: read`
- `issues: read`
- `pull-requests: write`
- `copilot-requests: write`

## API / Interface

`workflow_call` contract:

- Input `shared-proceed` (string, required)
- Input `shared-allowed-pr-authors-json` (string, required)
- Input `shared-allowed-pr-authors-csv` (string, required)
- Input `shared-allowed-issue-authors-json` (string, required)
- Input `shared-allowed-issue-authors-csv` (string, required)
- Input `shared-token-policy` (string, required)
- Secret: `BUILDKITE_API_TOKEN` (`required: true`)

Migration note for consumers: if you previously configured the consumer-facing secret name as `BUILDKITE_API_TOKEN`, rename or duplicate it as `BUILDKITE_LOGS_API_TOKEN` in repository/organization secrets.

## References

- Status client template: [oblt-aw-client-template.md](oblt-aw-client-template.md) — registry id `estc-pr-buildkite-detective` in `trigger-oblt-aw-status.yml`
- Upstream lock: [elastic/ai-github-actions](https://github.com/elastic/ai-github-actions) — [`.github/workflows/gh-aw-estc-pr-buildkite-detective.lock.yml`](https://github.com/elastic/ai-github-actions/blob/main/.github/workflows/gh-aw-estc-pr-buildkite-detective.lock.yml)
- Upstream documentation: [elastic.github.io/ai-github-actions](https://elastic.github.io/ai-github-actions/workflows/gh-agent-workflows/estc-pr-buildkite-detective/)

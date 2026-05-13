# Workflow: `gh-aw-estc-pr-buildkite-detective.yml`

## Overview

Source file: [.github/workflows/gh-aw-estc-pr-buildkite-detective.yml](../../.github/workflows/gh-aw-estc-pr-buildkite-detective.yml)

Reusable wrapper that calls the locked PR Buildkite Detective workflow in [elastic/ai-github-actions](https://github.com/elastic/ai-github-actions). The client entrypoint (`oblt-aw` template) invokes `oblt-aw-ingress`, which runs this job when a Buildkite commit status check fails on a PR.

## Prerequisites

- Triggered via `workflow_call` from `oblt-aw-ingress.yml`.
- Required secret: `COPILOT_GITHUB_TOKEN`.
- Required secret: `BUILDKITE_API_TOKEN` — a Buildkite API token with read access to build logs for the repository's Buildkite organization. In consumer repositories, map this from `BUILDKITE_LOGS_API_TOKEN`.

## Usage

Ingress routes here when:

- `github.event_name == 'status'`,
- `github.event.state == 'failure'`, and
- `github.event.context` contains `buildkite`, and
- Dashboard gating allows `estc-pr-buildkite-detective` (or no dashboard issue is present, so all workflows are enabled).

The job `estc-pr-buildkite-detective` calls:

- [elastic/ai-github-actions/.github/workflows/gh-aw-estc-pr-buildkite-detective.lock.yml@copilot/reduce-comment-spamming](https://github.com/elastic/ai-github-actions/blob/copilot/reduce-comment-spamming/.github/workflows/gh-aw-estc-pr-buildkite-detective.lock.yml)

Behavior and agent instructions for the locked workflow are defined in [elastic/ai-github-actions](https://github.com/elastic/ai-github-actions).

## Configuration

Permissions:

- `actions: read`
- `contents: read`
- `issues: write`
- `pull-requests: write`

## API / Interface

`workflow_call` contract:

- Secret: `COPILOT_GITHUB_TOKEN` (`required: true`)
- Secret: `BUILDKITE_API_TOKEN` (`required: true`)

Migration note for consumers: if you previously configured the consumer-facing secret name as `BUILDKITE_API_TOKEN`, rename or duplicate it as `BUILDKITE_LOGS_API_TOKEN` in repository/organization secrets.

## References

- Ingress routing: [docs/workflows/oblt-aw-ingress.md](oblt-aw-ingress.md) — workflow id `estc-pr-buildkite-detective` in [workflow-registry.json](../../config/obs/workflow-registry.json)
- Upstream lock: [elastic/ai-github-actions](https://github.com/elastic/ai-github-actions) — [`.github/workflows/gh-aw-estc-pr-buildkite-detective.lock.yml`](https://github.com/elastic/ai-github-actions/blob/copilot/reduce-comment-spamming/.github/workflows/gh-aw-estc-pr-buildkite-detective.lock.yml)
- Upstream documentation: [elastic.github.io/ai-github-actions](https://elastic.github.io/ai-github-actions/workflows/gh-agent-workflows/estc-pr-buildkite-detective/)

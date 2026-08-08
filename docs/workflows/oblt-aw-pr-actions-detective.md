# Workflow: `oblt-aw-pr-actions-detective.yml`

## Overview

Source file: [.github/workflows/oblt-aw-pr-actions-detective.yml](../../.github/workflows/oblt-aw-pr-actions-detective.yml)

Reusable wrapper that calls the locked PR Actions Detective workflow in [elastic/ai-github-actions](https://github.com/elastic/ai-github-actions). The client template `trigger-oblt-aw-workflow-run.yml` calls this workflow for failed GitHub Actions workflow runs when prelude allows `obs:pr-actions-detective`.

## Usage

Ingress routes here when:

- `github.event_name == 'workflow_run'`,
- `github.event.workflow_run.conclusion == 'failure'`, and
- Dashboard gate passes for registry id `pr-actions-detective` (`enabled-workflows` contains `obs:pr-actions-detective`).

The job `pr-actions-detective` calls:

- [elastic/ai-github-actions/.github/workflows/gh-aw-pr-actions-detective.lock.yml@main](https://github.com/elastic/ai-github-actions/blob/main/.github/workflows/gh-aw-pr-actions-detective.lock.yml)

Behavior and agent instructions for the locked workflow are defined in [elastic/ai-github-actions](https://github.com/elastic/ai-github-actions).

## Configuration

Permissions:

- `actions: read`
- `contents: read`
- `issues: read`
- `pull-requests: write`

## References

- Client template: [oblt-aw-client-template.md](oblt-aw-client-template.md) — registry id `pr-actions-detective`
- Upstream lock: [elastic/ai-github-actions](https://github.com/elastic/ai-github-actions) — [`.github/workflows/gh-aw-pr-actions-detective.lock.yml`](https://github.com/elastic/ai-github-actions/blob/main/.github/workflows/gh-aw-pr-actions-detective.lock.yml)
- Upstream documentation: [elastic.github.io/ai-github-actions](https://elastic.github.io/ai-github-actions/workflows/gh-agent-workflows/pr-actions-detective/)

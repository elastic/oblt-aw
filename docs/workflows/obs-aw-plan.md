# Workflow: `obs-aw-plan.yml`

## Overview

Source file: [.github/workflows/obs-aw-plan.yml](../../.github/workflows/obs-aw-plan.yml)

Reusable wrapper that resolves per-invocation agentic assets, then calls the local GH-AW planning workflow in this repository. The client template `trigger-obs-aw-issue-comment.yml` routes created issue comments beginning with `/plan` here when prelude allows `obs:plan`.

The GH-AW planning workflow uses native repository-role authorization (`admin`, `maintainer`, `write`) and the wrapped issue-comment bridge does not use `author_association` as the security boundary.

## Prerequisites

- Triggered via `workflow_call` from `trigger-obs-aw-issue-comment.yml`.
- Issue comment must be on an issue, not a pull request.
- Outer routing uses `/plan` as the prefix for APM-efficiency only; the GH-AW workflow remains authoritative for command handling and role checks.

## Usage

Ingress routes here when:

- `github.event_name == 'issue_comment'` and `github.event.action == 'created'`, and
- `github.event.issue.pull_request == null`, and
- `startsWith(github.event.comment.body, '/plan')`, and
- dashboard gate passes for registry id `plan` (`enabled-workflows` contains `obs:plan`).

The resolve job calls:

- [`.github/workflows/aw-resolve-agentic-assets.yml`](../../.github/workflows/aw-resolve-agentic-assets.yml)

The planning job calls:

- [`.github/workflows/gh-aw-plan.lock.yml`](../../.github/workflows/gh-aw-plan.lock.yml)

## Safe outputs

Planning comments are limited by the GH-AW `add-comment` safe-output scope, and bounded follow-up issue creation is limited to five issues per run by the workflow's `create-issue-max` input.

## Configuration

Permissions:

- top-level: `contents: read`
- job `resolve-apm-assets`: `contents: read`, `id-token: write`
- job `plan`: `actions: read`, `contents: read`, `copilot-requests: write`, `id-token: write`, `issues: write`, `pull-requests: read`

## API / Interface

`workflow_call` contract:

- Required inputs: `shared-proceed`, `shared-allowed-pr-authors-json`, `shared-allowed-pr-authors-csv`, `shared-allowed-issue-authors-json`, `shared-allowed-issue-authors-csv`, and `shared-token-policy`.
- The wrapper forwards resolved `additional-instructions`, resolved `setup-commands`, and `shared-token-policy` to the local GH-AW workflow invocation.

## References

- Client template: [obs-aw-client-template.md](obs-aw-client-template.md) — registry id `plan`
- Workflow source: [`.github/workflows/gh-aw-plan.md`](../../.github/workflows/gh-aw-plan.md)
- Workflow lock: [`.github/workflows/gh-aw-plan.lock.yml`](../../.github/workflows/gh-aw-plan.lock.yml)
- APM resolver: [aw-resolve-agentic-assets.md](aw-resolve-agentic-assets.md)

# Workflow: `obs-aw-plan.yml`

## Overview

Source file: [.github/workflows/obs-aw-plan.yml](../../.github/workflows/obs-aw-plan.yml)

Reusable wrapper that resolves per-invocation agentic assets, then calls the local GH-AW planning workflow in this repository. The client template `trigger-obs-aw-issue-comment.yml` routes created issue comments beginning with `/plan` here when prelude allows `obs:plan`.

The GH-AW planning workflow uses native repository-role authorization (`admin`, `maintainer`, `write`). The wrapper also requires an `OWNER`, `MEMBER`, or `COLLABORATOR` association before invoking the privileged resolver; this is defense-in-depth for execution, while GH-AW roles remain the command authorization boundary.

## Prerequisites

- Triggered via `workflow_call` from `trigger-obs-aw-issue-comment.yml`.
- Issue comment must be on an issue, not a pull request.
- Outer routing uses `/plan` as the prefix and requires an `OWNER`, `MEMBER`, or `COLLABORATOR` association before the privileged resolver runs. This defense-in-depth execution guard prevents untrusted APM setup; the GH-AW workflow remains authoritative for command handling and role checks.

## Usage

Ingress routes here when:

- `github.event_name == 'issue_comment'` and `github.event.action == 'created'`, and
- `github.event.issue.pull_request == null`, and
- `startsWith(github.event.comment.body, '/plan')`, and
- `github.event.comment.author_association` is `OWNER`, `MEMBER`, or `COLLABORATOR`, and
- dashboard gate passes for registry id `plan` (`enabled-workflows` contains `obs:plan`).

The resolve job calls:

- [`.github/workflows/aw-resolve-agentic-assets.yml`](../../.github/workflows/aw-resolve-agentic-assets.yml)

The planning job calls:

- [`.github/workflows/gh-aw-plan.lock.yml`](../../.github/workflows/gh-aw-plan.lock.yml)

## Safe outputs

Planning comments are limited to issues by the GH-AW `add-comment` safe-output scope, and bounded follow-up issue creation is limited to five issues per run by the workflow's `create-issue-max` input.

## Configuration

Permissions:

- top-level: `contents: read`
- job `resolve-apm-assets`: `contents: read`, `id-token: write`
- job `plan`: `actions: read`, `contents: read`, `copilot-requests: write`, `issues: write`, `pull-requests: read`

## API / Interface

`workflow_call` contract:

- Required inputs: `shared-proceed`, `shared-allowed-pr-authors-json`, `shared-allowed-pr-authors-csv`, `shared-allowed-issue-authors-json`, and `shared-allowed-issue-authors-csv`.
- The wrapper forwards resolved `additional-instructions` and resolved `setup-commands` to the local GH-AW workflow invocation, which uses the automatic `GITHUB_TOKEN`.
- Model selection is inherited from the shared Observability GH-AW defaults; this workflow exposes no model input.

## References

- Client template: [obs-aw-client-template.md](obs-aw-client-template.md) — registry id `plan`
- Workflow source: [`.github/workflows/gh-aw-plan.md`](../../.github/workflows/gh-aw-plan.md)
- Workflow lock: [`.github/workflows/gh-aw-plan.lock.yml`](../../.github/workflows/gh-aw-plan.lock.yml)
- APM resolver: [aw-resolve-agentic-assets.md](aw-resolve-agentic-assets.md)

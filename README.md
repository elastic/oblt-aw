# OBLT Agentic Workflows (`oblt-aw`)

This repository is the central catalog of reusable agentic workflows for Observability automation.

## Documentation

All documentation now lives under `docs/`.

- Docs home: `docs/README.md`
- Architecture and design: `docs/architecture/overview.md`
- Workflow-specific docs: `docs/workflows/README.md`
- Routing docs: `docs/routing/README.md`
- Distribution and rollout operations: `docs/operations/distribute-client-workflow.md`

## Quick Start

Target repositories should consume only this reusable entrypoint:

- `elastic/oblt-aw/.github/workflows/oblt-aw-ingress.yml@main`

Reference client workflow template:

- `.github/remote-workflow-template/oblt-aw.yml`

## Repository Scope

The primary executable workflows are in `.github/workflows/`, and their documentation is maintained in `docs/workflows/`.

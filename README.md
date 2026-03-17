# OBLT Agentic Workflows (`oblt-aw`)

This repository is the central catalog of reusable agentic workflows for Observability automation.

## Documentation

Primary repository documentation lives under `docs/`. Workflow routing implementation notes are maintained under `.github/workflow-routing/`.

- Docs home: `docs/README.md`
- Architecture and design: `docs/architecture/overview.md`
- Workflow-specific docs: `docs/workflows/README.md`
- Routing docs: `docs/routing/README.md`
- Workflow routing implementation notes: `.github/workflow-routing/`
- Distribution and rollout operations: `docs/operations/distribute-client-workflow.md`
- Contributing and local setup: `docs/development/contributing.md`

## Development

Before opening a PR:

1. Install [pre-commit](https://pre-commit.com/) and run `pre-commit install`
2. Run `pre-commit run --all-files` to validate locally
3. Run `pytest tests/` and `npm test` for Python and TypeScript tests

See `docs/development/contributing.md` for full setup and check details.

## Quick Start

Target repositories should consume only this reusable entrypoint:

- `elastic/oblt-aw/.github/workflows/oblt-aw-ingress.yml@main`

Reference client workflow template:

- `.github/remote-workflow-template/oblt-aw.yml`

## Repository Scope

The primary executable workflows are in `.github/workflows/`, and their documentation is maintained in `docs/workflows/`.

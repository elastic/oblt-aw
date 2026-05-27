# OBLT Agentic Workflows (`oblt-aw`)

This repository is the central catalog of reusable agentic workflows for Observability automation.

## Documentation

Primary repository documentation lives under `docs/`. Workflow routing documentation lives under `docs/routing/`.

- Docs home: [docs/README.md](docs/README.md)
- Architecture and design: [docs/architecture/overview.md](docs/architecture/overview.md)
- Workflow-specific docs: [docs/workflows/README.md](docs/workflows/README.md)
- Routing docs: [docs/routing/README.md](docs/routing/README.md)
- Distribution and rollout operations: [docs/operations/distribute-client-workflow.md](docs/operations/distribute-client-workflow.md)
- Contributing and local setup: [docs/development/contributing.md](docs/development/contributing.md)

## Development

Before opening a PR:

1. Install [pre-commit](https://pre-commit.com/) and run `pre-commit install`
2. Run `pre-commit run --all-files` to validate locally
3. Run `pytest tests/` and `npm test` for Python and TypeScript tests

See [docs/development/contributing.md](docs/development/contributing.md) for full setup and check details.

## Quick Start

Target repositories install per-workflow client templates from this repository (for example `trigger-oblt-aw-automerge.yml`, `oblt-aw-issue-fixer.yml`). Each template calls a matching `oblt-aw-*` reusable workflow; shared gating runs in [aw-prelude.yml](.github/workflows/aw-prelude.yml).

- Observability templates: [.github/remote-workflow-template/obs/.github/workflows/](.github/remote-workflow-template/obs/.github/workflows/) — see [docs/workflows/oblt-aw-client-template.md](docs/workflows/oblt-aw-client-template.md)
- Docs templates: [.github/remote-workflow-template/docs/.github/workflows/](.github/remote-workflow-template/docs/.github/workflows/) (`trigger-docs-aw-ai-menu.yml`, `trigger-docs-aw-pr-ai-menu.yml`)

## Repository Scope

The primary executable workflows are in [.github/workflows/](.github/workflows/), and their documentation is maintained in [docs/workflows/](docs/workflows/).

# OBLT Agentic Workflows (`oblt-aw`)

This repository is the central catalog of reusable agentic workflows for Observability automation.

## Documentation

Primary repository documentation lives under [docs/](docs/). Workflow routing implementation notes are maintained under [.github/workflow-routing/](.github/workflow-routing/).

- Docs home: [docs/README.md](docs/README.md)
- Architecture and design: [docs/architecture/overview.md](docs/architecture/overview.md)
- Workflow-specific docs: [docs/workflows/README.md](docs/workflows/README.md)
- Routing docs: [docs/routing/README.md](docs/routing/README.md)
- Workflow routing implementation notes: [.github/workflow-routing/](.github/workflow-routing/)
- Distribution and rollout operations: [docs/operations/distribute-client-workflow.md](docs/operations/distribute-client-workflow.md)
- Contributing and local setup: [docs/development/contributing.md](docs/development/contributing.md)

## Development

Before opening a PR:

1. Install [pre-commit](https://pre-commit.com/) and run `pre-commit install`
2. Run `pre-commit run --all-files` to validate locally
3. Run `pytest tests/` and `npm test` for Python and TypeScript tests

See [docs/development/contributing.md](docs/development/contributing.md) for full setup and check details.

## Quick Start

Target repositories should consume only this reusable entrypoint:

- [elastic/oblt-aw/.github/workflows/oblt-aw-ingress.yml@main](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/oblt-aw-ingress.yml)

Reference client workflow template:

- [.github/remote-workflow-template/oblt-aw.yml](.github/remote-workflow-template/oblt-aw.yml)

## Repository Scope

The primary executable workflows are in [.github/workflows/](.github/workflows/), and their documentation is maintained in [docs/workflows/](docs/workflows/).

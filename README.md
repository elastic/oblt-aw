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

Target repositories install event-scoped client templates from this repository (for example `trigger-oblt-aw-pull-request.yml`, `trigger-oblt-aw-issues.yml`). Each event client calls an `oblt-aw-event-*` orchestrator that runs shared dashboard gating via [aw-prelude.yml](.github/workflows/aw-prelude.yml) and passes `shared-proceed` (plus allow-list fields) into each route reusable.

- Observability templates: [.github/remote-workflow-template/obs/.github/workflows/](.github/remote-workflow-template/obs/.github/workflows/) — see [docs/workflows/oblt-aw-client-template.md](docs/workflows/oblt-aw-client-template.md)
- Docs templates: [.github/remote-workflow-template/docs/.github/workflows/](.github/remote-workflow-template/docs/.github/workflows/) (`trigger-docs-aw-issues.yml`, `trigger-docs-aw-issue-comment.yml`, `trigger-docs-aw-pull-request.yml`, `trigger-docs-aw-workflow-run.yml`)

## Repository Scope

The primary executable workflows are in [.github/workflows/](.github/workflows/), and their documentation is maintained in [docs/workflows/](docs/workflows/).

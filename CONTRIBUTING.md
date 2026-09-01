# Contributing

Thank you for contributing to oblt-aw. Please follow the guidelines below.

## Quick Start

1. **Install pre-commit** and run `pre-commit install`
2. **Run checks** before pushing: `pre-commit run --all-files`
3. **On a fresh checkout, install test dependencies once**: `pip install pytest==9.0.2` and `npm ci`
4. **Run tests**: `pytest tests/` and `npm test`

## Full Guide

See [docs/development/contributing.md](docs/development/contributing.md) for:

- Prerequisites (Python 3.14, Node.js 24, pre-commit)
- One-time setup
- Running individual checks
- Pre-commit hook reference
- CI workflow overview

## Client entrypoint workflows (`trigger-obs-aw-*.yml`)

Edit only the distributed client templates under [`.github/remote-workflow-template/`](.github/remote-workflow-template/) (for example [`.github/remote-workflow-template/obs/.github/workflows/`](.github/remote-workflow-template/obs/.github/workflows/) for Observability and [`.github/remote-workflow-template/docs/.github/workflows/`](.github/remote-workflow-template/docs/.github/workflows/) for Docs). See [docs/workflows/obs-aw-client-template.md](docs/workflows/obs-aw-client-template.md) and [docs/workflows/docs-aw-client-template.md](docs/workflows/docs-aw-client-template.md).

Details: [docs/workflows/obs-aw-client-template.md](docs/workflows/obs-aw-client-template.md).

## CI

All pull requests must pass CI. The workflow runs on every PR to `main`. See [docs/workflows/ci.md](docs/workflows/ci.md) for details.

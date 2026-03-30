# Contributing

Thank you for contributing to oblt-aw. Please follow the guidelines below.

## Quick Start

1. **Install pre-commit** and run `pre-commit install`
2. **Run checks** before pushing: `pre-commit run --all-files`
3. **Run tests**: `pytest tests/` and `npm test`

## Full Guide

See [docs/development/contributing.md](docs/development/contributing.md) for:

- Prerequisites (Python 3.13, Node.js 20+, pre-commit)
- One-time setup
- Running individual checks
- Pre-commit hook reference
- CI workflow overview

## Client entrypoint workflow (`oblt-aw.yml`)

Edit only [`.github/remote-workflow-template/oblt-aw.yml`](.github/remote-workflow-template/oblt-aw.yml). **Do not modify** [`.github/workflows/oblt-aw.yml`](.github/workflows/oblt-aw.yml) in this repository (enforced for Cursor via [`.cursor/rules/protected-oblt-aw-workflow.mdc`](.cursor/rules/protected-oblt-aw-workflow.mdc) and [AGENTS.md](AGENTS.md)).

Details: [docs/workflows/oblt-aw-client-template.md](docs/workflows/oblt-aw-client-template.md).

## CI

All pull requests must pass CI. The workflow runs on every PR to `main`. See [docs/workflows/ci.md](docs/workflows/ci.md) for details.

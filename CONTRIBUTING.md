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

## CI

All pull requests must pass CI. The workflow runs on every PR to `main`. See [docs/workflows/ci.md](docs/workflows/ci.md) for details.

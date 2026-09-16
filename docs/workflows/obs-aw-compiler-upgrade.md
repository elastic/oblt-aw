## Overview

Source file: [.github/workflows/obs-aw-compiler-upgrade.md](../../.github/workflows/obs-aw-compiler-upgrade.md)

This reusable workflow checks whether the pinned gh-aw compiler version in `.aw-compiler-version` is behind the latest upstream release and opens an issue only when an actionable upgrade is available.

## Prerequisites

- Triggered via `workflow_call`.

## Usage

This workflow runs directly as a gh-aw source workflow and compiles to a generated lock file in `.github/workflows/`.

Repository-specific instructions require the agent to:

- read the pinned compiler version from `.aw-compiler-version`
- compare it to the newest `github/gh-aw` release tags
- no-op when the pinned version is already current
- analyze release notes for breaking changes, relevant bug fixes, and non-breaking follow-up work
- open a GitHub issue only when an upgrade is available and worth tracking

## Configuration

Permissions:

- `actions: read`
- `contents: read`
- `issues: write`
- `copilot-requests: write`
- `id-token: write`

## API / Interface

`workflow_call` contract:

- Inputs: shared prelude gate and allow-list / token-policy inputs (`shared-proceed`, `shared-allowed-pr-authors-*`, `shared-allowed-issue-authors-*`, `shared-token-policy`).

## References

- Routing rules: none

## Overview

Source file: [.github/workflows/obs-aw-compiler-upgrade.md](../../.github/workflows/obs-aw-compiler-upgrade.md)

This workflow source checks whether the pinned gh-aw compiler version in `.aw-compiler-version` is behind the latest upstream release and opens an issue only when an actionable upgrade is available.

## Prerequisites

- Triggered on the weekly schedule or manually via `workflow_dispatch`.

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

- job `activation`: `actions: read`, `contents: read`
- job `agent`: `contents: read`, `copilot-requests: write`, `issues: read`
- job `conclusion`: `actions: read`, `issues: write`
- job `detection`: `contents: read`, `copilot-requests: write`
- job `safe_outputs`: `issues: write`

## API / Interface

Supported triggers:

- `schedule`: runs every Monday at 06:00 UTC.
- `workflow_dispatch`: accepts an optional `title-prefix` input for created issues.

## References

- Routing rules: none

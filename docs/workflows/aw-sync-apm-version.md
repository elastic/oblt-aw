# Workflow: `aw-sync-apm-version.yml`

## At a glance

| | |
| --- | --- |
| Platform | GitHub Actions |
| Source | [`.github/workflows/aw-sync-apm-version.yml`](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/aw-sync-apm-version.yml) |
| Trigger | Pull requests changing `.apm-cli-pin/requirements.txt` or `.apm.version`; manual dispatch |

## Purpose

Keeps the repository's `.apm.version` file aligned with the pinned `apm-cli` requirement. The workflow comment identifies the requirements file as the Dependabot-updated source of truth; the version file is consumed by agentic asset resolution and automerge classification.

## Execution flow

The single `sync-apm-version` job runs on `ubuntu-latest`. For pull requests it proceeds only when the PR comes from this repository; manual dispatch is also allowed. It parses an exact `apm-cli==X.Y.Z` pin, exits with an error if it cannot find one, and does nothing when `.apm.version` already matches. Otherwise it commits and pushes the updated version file using the GitHub Actions bot identity.

## Inputs, outputs, and access

There are no workflow inputs, outputs, or secrets. Workflow permissions default to `contents: read`; the job requests `contents: write` for the commit and push.

## Sources

- [Workflow](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/aw-sync-apm-version.yml)
- [Agentic asset resolver](aw-resolve-agentic-assets.md)

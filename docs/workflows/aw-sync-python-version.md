# Workflow: `aw-sync-python-version.yml`

## At a glance

| | |
| --- | --- |
| Platform | GitHub Actions |
| Source | [`.github/workflows/aw-sync-python-version.yml`](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/aw-sync-python-version.yml) |
| Trigger | Pull requests changing `.python-version` or synced pin targets; manual dispatch |

## Purpose

Keeps agent GH-AW fragments and the CI pre-commit action input aligned with the root [`.python-version`](https://github.com/elastic/oblt-aw/blob/main/.python-version) file. That file is the bumpable source of truth. Agent jobs check out consumer repositories, so they cannot read this repo's `.python-version` at runtime; the sync script bakes the pin into compiled setup steps instead. Control-plane `actions/setup-python` steps use `python-version-file: .python-version` and follow the file directly. Shared `runtime-setup` only installs Python (control-plane pin) and optional consumer Node; it does not install Go, Ruby, or uv.

## Execution flow

The single `sync-python-version` job runs on `ubuntu-latest`. For pull requests it proceeds only when the PR comes from this repository; manual dispatch is also allowed. It runs `scripts/sync_python_version.py`, and when fragments or `ci.yml` change it commits and pushes with the GitHub Actions bot identity. After fragment updates, recompile locks with `make compile-aw-check`.

## Inputs, outputs, and access

There are no workflow inputs, outputs, or secrets. Workflow permissions default to `contents: read`; the job requests `contents: write` for the commit and push.

## Sources

- [Workflow](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/aw-sync-python-version.yml)
- [Sync script](https://github.com/elastic/oblt-aw/blob/main/scripts/sync_python_version.py)

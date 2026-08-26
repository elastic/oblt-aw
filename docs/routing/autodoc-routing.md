# Autodoc Routing

## Overview

Client template: `trigger-obs-aw-autodoc.yml` → `obs-aw-autodoc.yml`

Routed workflow source: `.github/workflows/obs-aw-autodoc.yml`

## Usage

Ingress routes to autodoc when:

- `github.event_name == 'schedule'`
- The Control Plane dashboard gate allows registry id `autodoc` (see `docs/workflows/aw-prelude.md` — `get-enabled-workflows` / `enabled-workflows`)

The event name is evaluated in the context of the workflow run that invoked the ingress (`workflow_call`).

## Routed workflow

- `schedule` → `obs-aw-autodoc.yml`

## Notes

- `obs-aw-autodoc.yml` uses two upstream workflows from `elastic/ai-github-actions`:
  - `gh-aw-docs-patrol.lock.yml` — detects code changes that require documentation updates and creates an issue with findings
  - `gh-aw-create-pr-from-issue.lock.yml` — implements the findings and opens a PR (only when an issue was created)
- It is intended to analyze repository documentation and open a focused documentation PR.
- It must not merge PRs automatically.

## References

- `docs/workflows/obs-aw-autodoc.md`

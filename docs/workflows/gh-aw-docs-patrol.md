# Agentic workflow source: `gh-aw-docs-patrol.md`

## At a glance

| | |
| --- | --- |
| Platform | GitHub Agentic Workflows |
| Authored source | [`.github/workflows/gh-aw-docs-patrol.md`](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/gh-aw-docs-patrol.md) |
| Generated lock | [`.github/workflows/gh-aw-docs-patrol.lock.yml`](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/gh-aw-docs-patrol.lock.yml) |
| Invocation | `workflow_call`; called by the autodoc route |

## Purpose

Audits recent commits and the repository documentation inventory for concrete documentation drift or gaps. The authored prompt directs the agent to prefer no action unless a finding meets its quality gate; qualifying findings create a single issue.

## Execution flow

The source specifies a one-day commit lookback, dynamic discovery of common documentation paths, and checks for public interface, behavior, tooling, structural, and configuration changes. It excludes test-only/internal changes, generated content, and other explicitly listed false-positive categories. The workflow's safe output can create at most one issue, with a seven-day expiry policy.

The route passes additional instructions for the live autodoc E2E. In that mode, the source requires evaluating only the checked-in bait file and filing exactly one issue containing the marker; normal scheduled runs skip that bait.

## Inputs, outputs, and access

`workflow_call` optionally accepts `additional-instructions`. The workflow is restricted to admins, maintainers, writers, and `github-actions[bot]`; it requests `copilot-requests: write` and read-only repository, issue, PR, and Actions access. No secrets are declared in the source.

## Operational notes

The `.md` file is the authored gh-aw source; the `.lock.yml` is generated. Edit the source and run `make compile-aw-check` rather than editing the lock directly.

## Sources

- [Authored workflow source](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/gh-aw-docs-patrol.md)
- [Generated lock](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/gh-aw-docs-patrol.lock.yml)
- [Autodoc route](obs-aw-autodoc.md)
- [Autodoc E2E](e2e-autodoc.md)
- [Shared workflow fragments](https://github.com/elastic/oblt-aw/tree/main/.github/workflows/gh-aw-fragments)

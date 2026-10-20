# Agentic workflow source: `gh-aw-create-pr-from-issue.md`

## At a glance

| | |
| --- | --- |
| Platform | GitHub Agentic Workflows |
| Authored source | [`.github/workflows/gh-aw-create-pr-from-issue.md`](../../.github/workflows/gh-aw-create-pr-from-issue.md) |
| Generated lock | [`.github/workflows/gh-aw-create-pr-from-issue.lock.yml`](../../.github/workflows/gh-aw-create-pr-from-issue.lock.yml) |
| Invocation | `workflow_call` with a required target issue number |

## Purpose

Implements an issue and proposes a documentation-only pull request. The authored prompt describes the agent's role, safe-output contract, and scope; the compiled lock is the runnable GitHub Actions workflow.

## Invocation and behavior

The call requires `target-issue-number` and optionally accepts `additional-instructions`; `EXTRA_COMMIT_GITHUB_TOKEN` is optional. The workflow is restricted to admins, maintainers, writers, and the GitHub Actions bot. It serializes work per target issue.

The agent can read and edit repository files and run tests, but cannot directly commit or push. Its safe outputs may add one comment to the target issue and create a ready-for-review PR. PR changes are limited to Markdown/AsciiDoc/reStructuredText paths, with protected repository documents excluded from automatic edits.

## Access and outputs

The workflow declares `copilot-requests: write` and read-only contents/issues/pull-request/actions permissions. The safe-output PR operation is the only route for proposing changes. The generated workflow includes runtime setup, network and MCP tools from shared fragments.

## Operational notes

Edit the `.md` source, then regenerate and verify the lock with `make compile-aw-check`. Do not hand-edit the lock. The compiled workflow's exact behavior also depends on the imported files under `gh-aw-fragments/`.

## Sources

- [Authored workflow source](../../.github/workflows/gh-aw-create-pr-from-issue.md)
- [Generated lock](../../.github/workflows/gh-aw-create-pr-from-issue.lock.yml)
- [Shared workflow fragments](../../.github/workflows/gh-aw-fragments/)

# Agentic workflow source: `gh-aw-dependency-review.md`

## At a glance

| | |
| --- | --- |
| Platform | GitHub Agentic Workflows |
| Authored source | [`.github/workflows/gh-aw-dependency-review.md`](../../.github/workflows/gh-aw-dependency-review.md) |
| Generated lock | [`.github/workflows/gh-aw-dependency-review.lock.yml`](../../.github/workflows/gh-aw-dependency-review.lock.yml) |
| Invocation | Reusable workflow source; compiled implementation is called by the dependency-review route |

## Purpose

Analyzes Dependabot, Renovate, and Updatecli dependency-update pull requests. The source instructs the agent to classify changed versions and pins, review exact-version release notes and CVEs, assess local usage, and post an analysis comment with optional merge-ready labels. It is read-only apart from those outputs.

## Execution flow

Before the agent starts, a runner-side step downloads the Actions commit-verification collector from an immutable repository commit, verifies its SHA-256, and writes the facts consumed by the agent. Optional repository setup commands run afterward. The agent reads the PR diff, classifies dependency updates across the supported ecosystems, checks local usage and upstream security/release information, and emits a comment plus optional labels through safe outputs.

The route resolves APM assets before calling the compiled workflow and has a `notify-no-comment` job when the agent finishes successfully without posting analysis. See [Observability dependency review](obs-aw-dependency-review.md) and [PR event routing](obs-aw-event-pull-request.md).

## Inputs, outputs, and access

`workflow_call` accepts optional `additional-instructions`, `setup-commands`, and `github-token-policy`; optional secret `GH_AW_GITHUB_TOKEN` is also declared. The token policy can mint an ephemeral OIDC token, with secret/token fallbacks in the source. The allowed roles are admin, maintainer, and write; the source lists Dependabot, Renovate, Mergify, GitHub Actions, and Elastic bot identities.

Permissions are `copilot-requests: write`, `actions: read`, `contents: read`, `issues: read`, `pull-requests: read`, and `id-token: write`. Safe outputs are an analysis comment and optional labels; the workflow does not push code or modify the pull request.

## Operational notes

Edit the `.md` source, then run `make compile-aw-check` to regenerate and verify the lock. Do not hand-edit the generated lock.

## Sources

- [Authored workflow source](../../.github/workflows/gh-aw-dependency-review.md)
- [Generated lock](../../.github/workflows/gh-aw-dependency-review.lock.yml)
- [Observability dependency-review documentation](obs-aw-dependency-review.md)
- [Shared workflow fragments](../../.github/workflows/gh-aw-fragments/)

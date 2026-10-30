# Agentic workflow source: `gh-aw-autoapprove.md`

## At a glance

| | |
| --- | --- |
| Platform | GitHub Agentic Workflows |
| Authored source | [`.github/workflows/gh-aw-autoapprove.md`](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/gh-aw-autoapprove.md) |
| Generated lock | [`.github/workflows/gh-aw-autoapprove.lock.yml`](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/gh-aw-autoapprove.lock.yml) |
| Invocation | Reusable workflow source; compiled implementation is called by the automerge `approve` job |

## Purpose

Observability-owned **autoapprove** for eligible automerge pull requests. The agent re-checks author allow list, `oblt-aw/ai/merge-ready`, draft/fork/ref gates, then submits a pull request review with `event=APPROVE` when all gates pass. On failure it does nothing (no request-changes, no COMMENT-as-eligibility).

This is **not** a port of upstream `gh-aw-mention-in-pr`. It does not offer general PR chat, code push, or inline review-comment product surface.

## Execution flow

The automerge wrapper runs `verify` and dependency-collection first, resolves consumer APM assets, then calls the compiled lock. The agent evaluates the gates in the source prompt and either submits `APPROVE` or exits without a review. Downstream `assert-approved-review` still requires a real non-author `APPROVED` review before merge. See [Observability automerge](obs-aw-automerge.md) and [Automerge routing](../routing/automerge-routing.md).

## Inputs, outputs, and access

`workflow_call` accepts optional `additional-instructions` and `github-token-policy`; optional secret `GH_AW_GITHUB_TOKEN` is also declared. Resolved APM additional instructions are appended to the authored prompt. The lock does **not** accept `setup-commands` — approve only needs PR metadata, so consumer setup (for example `npm ci`) is not eval'd outside the agent sandbox while the job holds `id-token: write`. When `github-token-policy` is set, the lock mints an OIDC ephemeral token so the review is submitted as the Vault app (needed when the PR author is `github-actions[bot]` to avoid self-APPROVE). Empty policy uses `GITHUB_TOKEN` / `github-actions[bot]`.

Allowed roles are admin, maintainer, and write. Bot actors, `trusted-users`, and the prompt author list are synced from [allowed_pr_authors.json](https://github.com/elastic/oblt-aw/blob/main/config/obs/allowed_pr_authors.json) (GH-AW needs a static `on.bots` list; it cannot take that list from a `workflow_call` input). Run `make sync-allowed-pr-authors` after editing the JSON.

Permissions are `copilot-requests: write`, `actions: read`, `contents: read`, `issues: read`, `pull-requests: read`, and `id-token: write`. The only intended safe output is `submit-pull-request-review`.

## Cutover and rollback

Cutover: `obs-aw-automerge.yml` `approve` uses `./.github/workflows/gh-aw-autoapprove.lock.yml` (under [#2451](https://github.com/elastic/oblt-aw/issues/2451) / [#1876](https://github.com/elastic/oblt-aw/issues/1876)).

Rollback to the prior upstream lock:

```yaml
uses: elastic/ai-github-actions/.github/workflows/gh-aw-mention-in-pr.lock.yml@main
```

Leave upstream `gh-aw-mention-in-pr` in `elastic/ai-github-actions` for other consumers.

## Operational notes

Edit `config/obs/allowed_pr_authors.json` for the allow list, then `make sync-allowed-pr-authors` (or rely on the pre-commit hook) before `make compile-aw-check`. Edit other prompt/gate text in the `.md` source, then compile. Do not hand-edit the generated lock.

## Sources

- [Authored workflow source](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/gh-aw-autoapprove.md)
- [Generated lock](https://github.com/elastic/oblt-aw/blob/main/.github/workflows/gh-aw-autoapprove.lock.yml)
- [Observability automerge documentation](obs-aw-automerge.md)
- [Shared workflow fragments](https://github.com/elastic/oblt-aw/tree/main/.github/workflows/gh-aw-fragments)

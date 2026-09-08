# Workflow: `obs-aw-dependency-review.yml`

## Overview

Source file: [.github/workflows/obs-aw-dependency-review.yml](../../.github/workflows/obs-aw-dependency-review.yml)

This reusable workflow delegates dependency-update PR analysis to a locked workflow in [elastic/ai-github-actions](https://github.com/elastic/ai-github-actions).

## Prerequisites

- Triggered via `workflow_call`.
- Allow list: `needs.run-aw-prelude.outputs.allowed-pr-authors-csv` from [aw-prelude](aw-prelude.md) / [load-allowed-authors.yml](../../.github/workflows/load-allowed-authors.yml), derived from [config/obs/allowed_pr_authors.json](../../config/obs/allowed_pr_authors.json).

## Usage

The job `dependency-review` calls:

- [elastic/ai-github-actions/.github/workflows/gh-aw-dependency-review.lock.yml@main](https://github.com/elastic/ai-github-actions/blob/main/.github/workflows/gh-aw-dependency-review.lock.yml)

Forwarded inputs include:

- `allowed-bot-users`: from caller (CSV aligned with the control-plane allow list)
- `classification-labels`: `oblt-aw/ai/merge-ready`
- `additional-instructions`: control-plane fragments plus Noop-when-not-applicable rules, CVE-focused and internal-change impact analysis instructions.
- `github-token-policy`: from `shared-token-policy` (`aw-prelude` / `workflow-token-policy`). When non-empty, the nested lock workflow mints an OIDC installation token in the same job that applies labels (labels then re-trigger downstream workflows). Empty keeps `GITHUB_TOKEN` (no re-trigger).

Shared GitHub-read/safe-output contract is composed from [`config/obs/instruction-fragments/dependency-review-github-read-and-safe-outputs.md`](../../config/obs/instruction-fragments/dependency-review-github-read-and-safe-outputs.md) via [`config/obs/instruction-fragment-map.json`](../../config/obs/instruction-fragment-map.json) (see [instruction fragments](../architecture/instruction-fragments.md)).

Noop semantics (in additional-instructions):

- When the PR has no dependency updates to review (no version bumps, no lockfile changes indicating dependency updates, or changes outside supported ecosystems), the agent MUST call `noop` and must NOT call `add_comment` (no analysis comment from the agent).
- When the PR has dependency updates but the agent cannot gather enough context, it MUST call `report_incomplete` (or `missing_tool` / `missing_data`) — not a text-only exit.
- Intentional `noop` still leaves `comment_id` empty, so `notify-no-comment` may still upsert a control-plane note on the PR (not an analysis comment).

Labeling semantics (in additional-instructions):

- The agent assigns overall risk (**low**, **low-to-moderate**, **moderate**, **high**). Add `oblt-aw/ai/merge-ready` when risk is **low** or **low-to-moderate**, including when changelogs include CVEs/GHSAs/security fixes (those do not block the label in those bands; document them in the analysis). Also require: no breaking changes affecting this repo, ecosystem checks pass, and workflows are testable or the dependency is dev-only. Do not add the label when risk is moderate or high, or when other gates fail.
- Label application: when all criteria are met, the agent MUST call `add_labels` with that label (not only recommend in the comment). The comment's "Labels Applied" section must reflect labels actually applied via `add_labels`; if none were applied, it must say "No labels applied."

`notify-no-comment` runs when the lock succeeds with an empty `comment_id` and **upserts** a single comment on the **triggering PR** (marker `obs-aw-dependency-review:notify-no-comment`) with the latest run URL and retry guidance. Re-runs on the same PR update that comment instead of posting duplicates. The lock call sets `report-failure-as-issue: false` so empty bailouts do not open a separate `[aw] … produced no safe outputs` meta-issue.

## Failure mode (empty safe outputs)

If the agent exits with text only and zero safe outputs, the lock may still report success with an empty `comment_id`. `notify-no-comment` then upserts a human-visible comment on the PR (run URL + retry guidance). Retry by pushing a new commit to the PR branch (or close/reopen) so `pull_request` re-runs dependency-review.

Empty-safe-outputs hardening for Elastic consumers is owned by this control-plane route (instruction fragment + `notify-no-comment`), not by duplicating that contract in the shared upstream prompt.

## Configuration

Permissions:

- **Workflow:** `contents: read`.
- **Job `dependency-review`:** `actions: read`, `contents: read`, `issues: write`, `pull-requests: write`, `copilot-requests: write`, `id-token: write` (OIDC for in-lock `create-token`).
- **Job `notify-no-comment`:** `pull-requests: write`.

## API / Interface

`workflow_call` contract:

- Inputs: shared prelude gate and allow-list / token-policy inputs (`shared-proceed`, `shared-allowed-pr-authors-*`, `shared-allowed-issue-authors-*`, `shared-token-policy`).

## References

- Routing rules: [docs/routing/dependency-review-routing.md](../routing/dependency-review-routing.md)

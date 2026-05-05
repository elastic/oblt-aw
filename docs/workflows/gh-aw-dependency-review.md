# Workflow: `gh-aw-dependency-review.yml`

## Overview

Source file: [.github/workflows/gh-aw-dependency-review.yml](../../.github/workflows/gh-aw-dependency-review.yml)

This reusable workflow delegates dependency-update PR analysis to a locked workflow in [elastic/ai-github-actions](https://github.com/elastic/ai-github-actions).

## Prerequisites

- Triggered via `workflow_call`.
- Required inputs: `allowed-bot-users` (comma-separated logins; ingress passes `needs.load-allowed-authors.outputs.allowed_pr_authors_csv` from [load-allowed-authors.yml](../../.github/workflows/load-allowed-authors.yml), derived from [config/obs/allowed_pr_authors.json](../../config/obs/allowed_pr_authors.json)).
- Required secret: `COPILOT_GITHUB_TOKEN`.

## Usage

The job `dependency-review` calls:

- [elastic/ai-github-actions/.github/workflows/gh-aw-dependency-review.lock.yml@main](https://github.com/elastic/ai-github-actions/blob/main/.github/workflows/gh-aw-dependency-review.lock.yml)

Forwarded inputs include:

- `allowed-bot-users`: from caller (CSV aligned with the control-plane allow list)
- `classification-labels`: `oblt-aw/ai/merge-ready`
- `additional-instructions`: Noop-when-not-applicable rules, CVE-focused and internal-change impact analysis instructions.

After `dependency-review`, the workflow runs `signal-dependency-review-followups`, which mints an ephemeral installation token and re-applies `oblt-aw/ai/merge-ready` (remove + add) when present. This emits a `labeled` event from the installation token so downstream follow-up workflows can run.

Noop semantics (in additional-instructions):

- When the PR has no dependency updates to review (no version bumps, no lockfile changes indicating dependency updates, or changes outside supported ecosystems), the agent MUST call `noop` and must NOT add any comment to the PR.

Labeling semantics (in additional-instructions):

- The agent assigns overall risk (**low**, **low-to-moderate**, **moderate**, **high**). Add `oblt-aw/ai/merge-ready` when risk is **low** or **low-to-moderate**, including when changelogs include CVEs/GHSAs/security fixes (those do not block the label in those bands; document them in the analysis). Also require: no breaking changes affecting this repo, ecosystem checks pass, and workflows are testable or the dependency is dev-only. Do not add the label when risk is moderate or high, or when other gates fail.
- Label application: when all criteria are met, the agent MUST call `add_labels` with that label (not only recommend in the comment). The comment's "Labels Applied" section must reflect labels actually applied via `add_labels`; if none were applied, it must say "No labels applied."

## Configuration

Permissions:

- **Workflow:** `actions: read`, `contents: read`.
- **Job `dependency-review`:** `actions: read`, `contents: read`, `issues: write`, `pull-requests: write`.
- **Job `signal-dependency-review-followups`:** `contents: read`, `id-token: write`, `pull-requests: write` (OIDC for ephemeral `create-token` and label re-apply signaling).

## API / Interface

`workflow_call` contract:

- Inputs: `allowed-bot-users` (`required: true`) — comma-separated GitHub logins for bot PR filtering
- Secret: `COPILOT_GITHUB_TOKEN` (`required: true`)

## References

- Routing rules: [docs/routing/dependency-review-routing.md](../routing/dependency-review-routing.md)

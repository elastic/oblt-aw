# Workflow: `obs-aw-dependency-review.yml`

## Overview

Source file: [.github/workflows/obs-aw-dependency-review.yml](../../.github/workflows/obs-aw-dependency-review.yml)

Reusable wrapper that calls the Observability-owned Dependency Review lock in this repository. Client `trigger-obs-aw-pull-request.yml` routes allowed-author `pull_request` events here when prelude allows `obs:dependency-review`.

Landing home for this primitive (under [#2098](https://github.com/elastic/oblt-aw/issues/2098) / [#1876](https://github.com/elastic/oblt-aw/issues/1876)): **`elastic/oblt-aw`**.

Instruction ownership for this import: **Merge**. Noop / CVE / merge-ready / GitHub-read safe-output rules live in [`.github/workflows/gh-aw-dependency-review.md`](../../.github/workflows/gh-aw-dependency-review.md). The control-plane fragment map no longer composes a dependency-review layer; `aw-resolve-agentic-assets` only merges consumer APM instructions.

## Prerequisites

- Triggered via `workflow_call` from the pull_request event orchestrator (`obs-aw-event-pull-request.yml` ← client `trigger-obs-aw-pull-request.yml`).
- Allow list for the route `if:` condition still comes from prelude / [config/obs/allowed_pr_authors.json](../../config/obs/allowed_pr_authors.json). Bot actors accepted by the lock are hardcoded to that same list on the GH-AW source.

## Usage

Ingress routes here when:

- `github.event_name == 'pull_request'`,
- action is `opened` / `synchronize` / `reopened`,
- author is on the allowed PR authors list, and
- Dashboard gate passes for registry id `dependency-review` (`enabled-workflows` contains `obs:dependency-review`).

The job `dependency-review` calls:

```yaml
uses: elastic/oblt-aw/.github/workflows/gh-aw-dependency-review.lock.yml@main
```

Edit the GH-AW source [`.github/workflows/gh-aw-dependency-review.md`](../../.github/workflows/gh-aw-dependency-review.md) and compile with `make compile-aw-check` from the repository root (do not hand-edit the lock). Compile also runs `scripts/wire_ephemeral_token.py` so minted `create-token` outputs win over `GITHUB_TOKEN` when `github-token-policy` is set.

### Opinionated vs preserved

| Opinionated (Observability-owned) | Preserved as lock inputs |
|-----------------------------------|--------------------------|
| Model, failure-issue suppression, and trusted-user baseline via [`.github/workflows/gh-aw-fragments/obs-defaults.md`](../../.github/workflows/gh-aw-fragments/obs-defaults.md) (trusted-users overridden on the workflow to the Obs allow list) | `additional-instructions` (from `aw-resolve-agentic-assets`) |
| Comment footer via [`.github/workflows/gh-aw-fragments/messages-footer.md`](../../.github/workflows/gh-aw-fragments/messages-footer.md) | `setup-commands` (joined from consumer `apm.yml` when non-empty) |
| Bots + `classification-labels` default `oblt-aw/ai/merge-ready` on the source (callers must not override `classification-labels`; the fragment sanitizer reads that input) | `github-token-policy` (from `shared-token-policy`) |
| Noop / CVE / merge-ready / GitHub-read rules in the prompt body | |

`notify-no-comment` runs when the lock succeeds with an empty `comment_id` and **upserts** a single comment on the **triggering PR** (marker `obs-aw-dependency-review:notify-no-comment`) with the latest run URL and retry guidance. Re-runs on the same PR update that comment instead of posting duplicates. Failure-issue suppression comes from `obs-defaults` (no `report-failure-as-issue` lock input).

## Failure mode (empty safe outputs)

If the agent exits with text only and zero safe outputs, the lock may still report success with an empty `comment_id`. `notify-no-comment` then upserts a human-visible comment on the PR (run URL + retry guidance). Retry by pushing a new commit to the PR branch (or close/reopen) so `pull_request` re-runs dependency-review.

## Configuration

Permissions:

- **Workflow:** `contents: read`.
- **Job `dependency-review`:** `actions: read`, `contents: read`, `issues: write`, `pull-requests: write`, `copilot-requests: write`, `id-token: write` (OIDC for in-lock `create-token`).
- **Job `notify-no-comment`:** `pull-requests: write`.

## API / Interface

Wrapper `workflow_call` contract:

- Inputs: `shared-proceed`, `shared-token-policy` (allow-list inputs were dropped from the wrapper after bots were hardcoded on the lock).

Lock inputs passed by the wrapper:

- `additional-instructions` — resolved consumer instructions
- `setup-commands` — `join(fromJSON(resolved-setup-commands-json), fromJSON('"\n"'))` from resolve
- `github-token-policy` — from `shared-token-policy`

The lock also declares `classification-labels` with default `oblt-aw/ai/merge-ready` so the `safe-output-add-labels` sanitizer can read it. The wrapper must not pass or override that input.

## Cutover and rollback

**Cutover:** the wrapper `uses` `elastic/oblt-aw/.../gh-aw-dependency-review.lock.yml@main` instead of `elastic/ai-github-actions/...@main`. Event routing and dashboard id are unchanged.

**Rollback:** point the wrapper job back at the previous upstream lock:

```yaml
uses: elastic/ai-github-actions/.github/workflows/gh-aw-dependency-review.lock.yml@main
```

and restore any upstream-required inputs (`allowed-bot-users`, `classification-labels`, `report-failure-as-issue`) if needed. Copies in `elastic/ai-github-actions` remain for other consumers; this cutover does not deprecate or remove them.

**Integration (no live model):** fixtures and wiring checks for resolve → wrapper → lock inputs live under [`testdata/agentic/dependency-review/`](../../testdata/agentic/dependency-review/) and [`tests/integration/test_dependency_review.py`](../../tests/integration/test_dependency_review.py).

**E2E:** production path on **`elastic/oblt-aw`** via [`.github/workflows/e2e-dependency-review.yml`](../../.github/workflows/e2e-dependency-review.yml) (`workflow_dispatch` / `workflow_call` from `e2e-all.yml`). Live happy path: Vault-authored Actions pin-bump PR → dependency-review comment + `oblt-aw/ai/merge-ready`. See [dependency-review-e2e](../testing/dependency-review-e2e.md).

## References

- Client template: [obs-aw-client-template.md](obs-aw-client-template.md) — registry id `dependency-review`
- Routing: [docs/routing/dependency-review-routing.md](../routing/dependency-review-routing.md)
- In-repo source: [`.github/workflows/gh-aw-dependency-review.md`](../../.github/workflows/gh-aw-dependency-review.md)
- In-repo lock: [`.github/workflows/gh-aw-dependency-review.lock.yml`](../../.github/workflows/gh-aw-dependency-review.lock.yml)
- Shared model defaults: [`.github/workflows/gh-aw-fragments/obs-defaults.md`](../../.github/workflows/gh-aw-fragments/obs-defaults.md)
- Prior upstream (rollback / other consumers): [elastic/ai-github-actions](https://github.com/elastic/ai-github-actions) — [`.github/workflows/gh-aw-dependency-review.lock.yml`](https://github.com/elastic/ai-github-actions/blob/main/.github/workflows/gh-aw-dependency-review.lock.yml)

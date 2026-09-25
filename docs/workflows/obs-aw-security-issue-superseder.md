# Workflow: `obs-aw-security-issue-superseder.yml`

## Overview

Source file: [.github/workflows/obs-aw-security-issue-superseder.yml](../../.github/workflows/obs-aw-security-issue-superseder.yml)

Deterministic supersession for security detector issues. When a **new** issue is opened with label `oblt-aw/detector/security`, this workflow closes **older open** issues for the **same SEC rule** and retires linked bot fix PRs when safe.

Implementation is a shell script ([`scripts/obs/supersede-security-issues.sh`](../../scripts/obs/supersede-security-issues.sh)); it does **not** call [elastic/ai-github-actions](https://github.com/elastic/ai-github-actions). See [elastic/observability-robots#4424](https://github.com/elastic/observability-robots/issues/4424).

## Prerequisites

- Invoked via `workflow_call` from [obs-aw-event-issues.yml](../../.github/workflows/obs-aw-event-issues.yml) (client template `trigger-obs-aw-issues.yml`).
- Dashboard gating uses registry id **`security`** (`obs:security`) — same compound id as detector, triage, and fixer.
- Ephemeral GitHub token from [`elastic/oblt-actions/github/create-token@v1`](https://github.com/elastic/oblt-actions/tree/v1/github/create-token) (same pattern as the security detector).

## Usage

Ingress routes here when:

- `github.event_name == 'issues'` and `github.event.action == 'opened'`, and
- The opened issue includes label `oblt-aw/detector/security`, and
- Prelude allows `obs-aw-security-issue-superseder.yml` (via `obs:security`).

Job **supersede-security-issues**:

1. Checks out `scripts/obs/supersede-security-issues.sh` from [elastic/oblt-aw](https://github.com/elastic/oblt-aw) at ref `main`.
2. Creates an ephemeral token when configured (Vault auto policy or repo `workflow-token-policy`).
3. Runs the script with the **canonical** issue number (`github.event.issue.number`).

### Supersession policy

| Rule | Behavior |
|------|----------|
| **Equivalence** | Same **SEC id** parsed from title `[oblt-aw][security] SEC-XXX — findings (…)` and label `oblt-aw/detector/security` |
| **Direction** | Newer issue (higher number) is canonical; only **older** open issues are candidates |
| **Skip close** | Candidate has `oblt-aw/keep-open` |
| **Skip close** | Candidate has any **open** PR linked via issue cross-references |

On supersede, the script posts a comment on the older issue linking to the canonical issue, then closes it.

## Configuration

Permissions (job **supersede-security-issues**):

| Permission | Purpose |
|------------|---------|
| `contents: read` | Sparse checkout of oblt-aw script |
| `id-token: write` | OIDC for `create-token` |
| `issues: write` | Comment and close superseded issues |
| `pull-requests: read` | Detect open linked PRs on candidate issues |

Environment passed to the script:

| Variable | Source |
|----------|--------|
| `GITHUB_REPOSITORY` | Caller repository |
| `GH_TOKEN` | Ephemeral token from `create-token` |

Set `DRY_RUN=1` locally to log actions without mutating GitHub.

## API / Interface

`workflow_call` contract (standard shared prelude inputs):

- `shared-proceed` (required)
- `shared-allowed-pr-authors-json` / `shared-allowed-pr-authors-csv` (required)
- `shared-allowed-issue-authors-json` / `shared-allowed-issue-authors-csv` (required)
- `shared-token-policy` (required; may be empty)

No secrets are declared on this workflow.

## References

- Client template: [obs-aw-client-template.md](obs-aw-client-template.md) — registry id `security`
- Script: [`scripts/obs/supersede-security-issues.sh`](../../scripts/obs/supersede-security-issues.sh)
- Issue creation (detector): [`scripts/obs/create-security-issues.sh`](../../scripts/obs/create-security-issues.sh)
- [Security agent architecture](../architecture/security-agent-architecture.md)
- [Security routing](../routing/security-routing.md)
- [elastic/observability-robots#4424](https://github.com/elastic/observability-robots/issues/4424)

# Workflow: `oblt-aw-ingress.yml`

## Overview

Source file: [.github/workflows/oblt-aw-ingress.yml](../../.github/workflows/oblt-aw-ingress.yml)

This is the reusable orchestration entrypoint for `oblt-aw`. It routes to specialized workflows based on event context.

## Prerequisites

- Called by consumer workflows using `workflow_call`.
- Optional secret: `COPILOT_GITHUB_TOKEN`.

## Usage

### Supported triggers

The workflow file declares only `workflow_call`.

Event triggers such as `schedule`, `workflow_dispatch`, `issues`, `issue_comment`, and `pull_request` are declared in caller workflows/templates (for example [.github/remote-workflow-template/obs/.github/workflows/oblt-aw.yml](../../.github/remote-workflow-template/obs/.github/workflows/oblt-aw.yml)). In ingress, routing conditions evaluate `github.event_name` and `github.event.action` from the caller event payload.

### Dashboard gating

The job `dashboard-enabled-workflows` runs `get-enabled-workflows.yml` first. Downstream jobs use `needs: dashboard-enabled-workflows` and gate on its outputs:

- `effective-raw` empty (no open dashboard issue) → every registry id is treated as enabled for jobs that check `enabled-workflows`.
- `effective-raw` non-empty and the normalized `enabled-workflows` array is `[]` → no gated jobs run.
- Non-empty `enabled-workflows` → only listed **compound ids** `org:workflow-id` pass the `contains(..., 'org:workflow-id')` checks (for example `obs:agent-suggestions`). Bare workflow ids without an org prefix are not accepted.

Jobs that do not list `needs: dashboard-enabled-workflows` are not gated this way (see [Internal ingress jobs](#internal-ingress-jobs-not-in-workflow-registryjson)).

### Allow lists (`load-allowed-authors`)

Ingress runs job `load-allowed-authors` only when `github.event_name` is `pull_request` or `issues`; it calls reusable workflow [.github/workflows/load-allowed-authors.yml](../../.github/workflows/load-allowed-authors.yml) in parallel with `dashboard-enabled-workflows` when that job runs. The reusable workflow **checks out** the public **`elastic/oblt-aw`** repository at `ref=main` with sparse paths [config/obs/allowed_pr_authors.json](https://github.com/elastic/oblt-aw/blob/main/config/obs/allowed_pr_authors.json) and [config/obs/allowed_issue_authors.json](https://github.com/elastic/oblt-aw/blob/main/config/obs/allowed_issue_authors.json) (same branch consumers pin with `uses: elastic/oblt-aw/.github/workflows/oblt-aw-ingress.yml@main`), then reads each file with `jq` into four outputs: `allowed_pr_authors_json`, `allowed_pr_authors_csv`, `allowed_issue_authors_json`, and `allowed_issue_authors_csv`. **Pull-request** jobs (`automerge`, `dependency-review`) use the **PR** JSON/CSV for author gating and `allowed-bot-users` on dependency review. **Specialized issue** paths (security triage/fixer, resource-not-accessible triage/fixer) pass **`allowed_issue_authors_csv`** into upstream `allowed-bot-users` for [elastic/ai-github-actions](https://github.com/elastic/ai-github-actions) issue triage/fixer locks. Generic **`issue-triage`** / **`issue-fixer`** do not pass that input (upstream defaults only; no control-plane issue author list). Consumer repositories do not need a copy of these files on disk for ingress routing.

Canonical registry ids and metadata live per org under `config/<org-key>/workflow-registry.json` (for example [config/obs/workflow-registry.json](../../config/obs/workflow-registry.json)). Ingress `enabled-workflows` entries use **`obs:<registry-id>`** for Observability workflows below.

## Routed workflows ([config/obs/workflow-registry.json](../../config/obs/workflow-registry.json))

The following subsections follow the order of entries in the Observability registry. Each subsection lists the registry fields and the ingress job(s) that honor that id in `enabled-workflows` as **`obs:<id>`**. Where a dedicated routing document exists under [docs/routing/](../routing/), the subsection includes a **Routing** link to it (labels, triggers, and dispatch detail).

### Agent suggestions (registry id `agent-suggestions`, gate `obs:agent-suggestions`)

**Routing:** [Agent suggestions routing](../routing/agent-suggestions-routing.md)

| Registry field | Value |
|----------------|--------|
| `id` | `agent-suggestions` |
| `name` | Agent Suggestions |
| `description` | Suggests agentic workflows and improvements for the repository based on analysis of current setup. |

| Ingress job | Reusable workflow | Triggers (from [.github/workflows/oblt-aw-ingress.yml](../../.github/workflows/oblt-aw-ingress.yml)) | Dashboard gate |
|-------------|-------------------|--------------------------------------------------------|----------------|
| `agent-suggestions` | `gh-aw-agent-suggestions.yml` | `schedule` | Yes — `enabled-workflows` must contain `obs:agent-suggestions` when `effective-raw` is non-empty |

### Automated documentation (registry id `autodoc`)

**Routing:** [Autodoc routing](../routing/autodoc-routing.md)

| Registry field | Value |
|----------------|--------|
| `id` | `autodoc` |
| `name` | Automated Documentation |
| `description` | Analyzes documentation for gaps, outdated content, and inconsistencies; creates issues and PRs to improve docs. |

| Ingress job | Reusable workflow | Triggers | Dashboard gate |
|-------------|-------------------|----------|----------------|
| `autodoc` | `gh-aw-autodoc.yml` | `schedule` | Yes — `obs:autodoc` |

### Automerge (registry id `automerge`)

**Routing:** [Automerge routing](../routing/automerge-routing.md)

| Registry field | Value |
|----------------|--------|
| `id` | `automerge` |
| `name` | Automerge |
| `description` | Enables auto-merge for allowed bot PRs (same authors as dependency-review) with `oblt-aw/ai/merge-ready` when validation, approval, and checks succeed. |

| Ingress job | Reusable workflow | Triggers | Dashboard gate |
|-------------|-------------------|----------|----------------|
| `automerge` | `gh-aw-automerge.yml` | `pull_request` `opened` / `synchronize` / `reopened` / `labeled` where PR author is in `load-allowed-authors` output **and** the PR has label `oblt-aw/ai/merge-ready` | Yes — `obs:automerge` |

Forwards `COPILOT_GITHUB_TOKEN` to `gh-aw-automerge.yml` for the Copilot-based approval step.

### Dependency review (registry id `dependency-review`)

**Routing:** [Dependency review routing](../routing/dependency-review-routing.md)

| Registry field | Value |
|----------------|--------|
| `id` | `dependency-review` |
| `name` | Dependency Review |
| `description` | Analyzes dependency-update PRs from bots, applies merge-ready labels when criteria are met. |

| Ingress job | Reusable workflow | Triggers | Dashboard gate |
|-------------|-------------------|----------|----------------|
| `dependency-review` | `gh-aw-dependency-review.yml` | `pull_request` `opened` / `synchronize` / `reopened`; PR author must appear in `load-allowed-authors` output (from [allowed_pr_authors.json](https://github.com/elastic/oblt-aw/blob/main/config/obs/allowed_pr_authors.json)) | Yes — `obs:dependency-review` |

This job is separate from registry id `security`: it is PR-time dependency and license review for bot PRs, not the static repo-wide security scan. See [docs/workflows/gh-aw-dependency-review.md](gh-aw-dependency-review.md) and [docs/workflows/security-scanning-ruleset.md](security-scanning-ruleset.md) (complementary workflows SEC-033–SEC-035).

### Duplicate issue detector (registry id `duplicate-issue-detector`)

| Registry field | Value |
|----------------|--------|
| `id` | `duplicate-issue-detector` |
| `name` | Duplicate Issue Detector |
| `description` | Detects potential duplicate issues when a new issue is opened or when the entrypoint is run manually. |

| Ingress job | Reusable workflow | Triggers | Dashboard gate |
|-------------|-------------------|----------|----------------|
| `duplicate-issue-detector` | `gh-aw-duplicate-issue-detector.yml` | `issues` `opened`, or `workflow_dispatch` | Yes — `obs:duplicate-issue-detector` |

### Issue triage (registry id `issue-triage`)

| Registry field | Value |
|----------------|--------|
| `id` | `issue-triage` |
| `name` | Issue Triage |
| `description` | Triages newly opened issues using the generic issue-triage agentic workflow. |

| Ingress job | Reusable workflow | Triggers | Dashboard gate |
|-------------|-------------------|----------|----------------|
| `issue-triage` | `gh-aw-issue-triage.yml` | `issues` `opened` | Yes — `obs:issue-triage` |

### Issue fixer (registry id `issue-fixer`)

**Routing:** [Issue fixer routing](../routing/issue-fixer-routing.md)

| Registry field | Value |
|----------------|--------|
| `id` | `issue-fixer` |
| `name` | Issue Fixer |
| `description` | Executes generic issue fixes requested with `/ai implement` comments, excluding specialized security and resource-not-accessible flows. |

| Ingress job | Reusable workflow | Triggers | Dashboard gate |
|-------------|-------------------|----------|----------------|
| `issue-fixer` | `gh-aw-issue-fixer.yml` | `issue_comment` `created` on an issue (not a PR) with comment starting `/ai implement`, and without `oblt-aw/triage/security-*` or `oblt-aw/triage/res-not-accessible-by-integration` | Yes — `obs:issue-fixer` |

### Mention in Issue (registry id `mention-in-issue`)

| Registry field | Value |
|----------------|--------|
| `id` | `mention-in-issue` |
| `name` | Mention in Issue |
| `description` | AI assistant for issues — answers questions, debugs problems, and creates PRs on demand when triggered by a /ai comment. |

| Ingress job | Reusable workflow | Triggers | Dashboard gate |
|-------------|-------------------|----------|----------------|
| `mention-in-issue` | `gh-aw-mention-in-issue.yml` | `issue_comment` `created` on an issue (not a PR) with comment starting with `/ai` and not starting with `/ai implement`, where `github.event.comment.author_association` is `OWNER`, `MEMBER`, or `COLLABORATOR` | Yes — `obs:mention-in-issue` |

### Security (registry id `security`)

**Routing:** [Security routing](../routing/security-routing.md)

| Registry field | Value |
|----------------|--------|
| `id` | `security` |
| `name` | Security |
| `description` | Runs static security checks on workflows, shell scripts, and dependency manifests per the security scanning ruleset; opens issues for findings. |

There is one registry id for the whole security pipeline. The Control Plane Dashboard uses that id for the Security checkbox; `enabled-workflows` lists compound id `obs:security` when consumers restrict runs.

| Ingress job | Reusable workflow | Triggers | Dashboard gate |
|-------------|-------------------|----------|----------------|
| `security-detector` | `gh-aw-security-detector.yml` | `schedule`, `workflow_dispatch` | Yes — `obs:security` |
| `security-triage` | `gh-aw-security-triage.yml` | `issues` `opened` with label `oblt-aw/detector/security`, or `issues` `labeled` with that label | Yes — `obs:security` |
| `security-fixer` | `gh-aw-security-fixer.yml` | `issues` `labeled` with `oblt-aw/ai/fix-ready` and a `oblt-aw/triage/security-*` label | Yes — `obs:security` |

Further reading:

- [docs/architecture/security-agent-architecture.md](../architecture/security-agent-architecture.md)
- [docs/workflows/gh-aw-security-detector.md](gh-aw-security-detector.md)
- [docs/workflows/gh-aw-security-triage.md](gh-aw-security-triage.md)
- [docs/workflows/gh-aw-security-fixer.md](gh-aw-security-fixer.md)

### Resource not accessible by integration (registry id `resource-not-accessible-by-integration`)

**Routing:** [Resource not accessible by integration routing](../routing/resource-not-accessible-by-integration-routing.md)

| Registry field | Value |
|----------------|--------|
| `id` | `resource-not-accessible-by-integration` |
| `name` | Resource Not Accessible by Integration |
| `description` | Detects 'Resource not accessible by integration' occurrences in workflow logs, creates triage issues, triages newly opened issues, and executes fixes for issues labeled ready to fix. |

One registry id covers detector, triage, and fixer.

| Ingress job | Reusable workflow | Triggers | Dashboard gate |
|-------------|-------------------|----------|----------------|
| `resource-not-accessible-by-integration-detector` | `gh-aw-resource-not-accessible-by-integration-detector.yml` | `schedule` | Yes — `obs:resource-not-accessible-by-integration` |
| `resource-not-accessible-by-integration-triage` | `gh-aw-resource-not-accessible-by-integration-triage.yml` | `issues` `opened` with `oblt-aw/detector/res-not-accessible-by-integration`, or `issues` `labeled` with that label | Yes — `obs:resource-not-accessible-by-integration` |
| `resource-not-accessible-by-integration-fixer` | `gh-aw-resource-not-accessible-by-integration-fixer.yml` | `issues` `labeled` with `oblt-aw/ai/fix-ready` and `oblt-aw/triage/res-not-accessible-by-integration` | Yes — `obs:resource-not-accessible-by-integration` |

## Internal ingress jobs (not in [workflow-registry.json](../../config/obs/workflow-registry.json))

These jobs exist only in [.github/workflows/oblt-aw-ingress.yml](../../.github/workflows/oblt-aw-ingress.yml) and do not have registry ids:

| Job | Role |
|-----|------|
| `dashboard-enabled-workflows` | Invokes `get-enabled-workflows.yml`; supplies `effective-raw` and `enabled-workflows` to gated jobs. See [docs/workflows/get-enabled-workflows.md](get-enabled-workflows.md). |
| `load-allowed-authors` | On `pull_request` or `issues` events only, invokes `load-allowed-authors.yml`; supplies PR and issue allow-list outputs from **`elastic/oblt-aw`** ([allowed_pr_authors.json](https://github.com/elastic/oblt-aw/blob/main/config/obs/allowed_pr_authors.json), [allowed_issue_authors.json](https://github.com/elastic/oblt-aw/blob/main/config/obs/allowed_issue_authors.json)). |
| `unsupported-trigger` | Runs when the event is not one of the supported combinations; fails the workflow with a clear message. It has no `needs: dashboard-enabled-workflows` and does not read the registry. |

## Configuration

Top-level permissions (matches [.github/workflows/oblt-aw-ingress.yml](../../.github/workflows/oblt-aw-ingress.yml)):

- `actions: write`
- `checks: read`
- `contents: write`
- `discussions: write`
- `id-token: write` (OIDC for nested reusable workflows that use ephemeral tokens, e.g. [gh-aw-security-detector.md](gh-aw-security-detector.md))
- `issues: write`
- `pull-requests: write`

## API / Interface

Interface exposed through `workflow_call`:

- Secret: `COPILOT_GITHUB_TOKEN` (`required: false`)

## Examples

Minimal consumer reference (client template calls ingress only; dashboard read runs inside ingress):

```yaml
jobs:
  run-aw:
    uses: elastic/oblt-aw/.github/workflows/oblt-aw-ingress.yml@main
    secrets:
      COPILOT_GITHUB_TOKEN: ${{ secrets.COPILOT_GITHUB_TOKEN }}
```

## References

- [workflow-registry.json](../../config/obs/workflow-registry.json) (canonical Observability workflow ids for the Control Plane Dashboard; other orgs use `config/<org-key>/workflow-registry.json`)
- [docs/workflows/get-enabled-workflows.md](get-enabled-workflows.md)
- [Routing documentation index](../routing/README.md)
- [Agent suggestions routing](../routing/agent-suggestions-routing.md)
- [Autodoc routing](../routing/autodoc-routing.md)
- [Automerge routing](../routing/automerge-routing.md)
- [Dependency review routing](../routing/dependency-review-routing.md)
- [Issue fixer routing](../routing/issue-fixer-routing.md)
- [Security routing](../routing/security-routing.md)
- [Resource not accessible by integration routing](../routing/resource-not-accessible-by-integration-routing.md)

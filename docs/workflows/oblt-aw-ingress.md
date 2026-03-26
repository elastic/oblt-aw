# Workflow: `oblt-aw-ingress.yml`

## Overview

Source file: `.github/workflows/oblt-aw-ingress.yml`

This is the reusable orchestration entrypoint for `oblt-aw`. It routes to specialized workflows based on event context.

## Prerequisites

- Called by consumer workflows using `workflow_call`.
- Optional secret: `COPILOT_GITHUB_TOKEN`.

## Usage

### Supported triggers

The workflow file declares support for:

- `schedule`
- `workflow_dispatch` (for example manual runs used by `duplicate-issue-detector` and `security-detector`)
- `workflow_call`
- `issues` with `opened` and `labeled`
- `pull_request` with `opened`, `synchronize`, `reopened`
- `pull_request_review` with `submitted`

### Dashboard gating

The job `dashboard-enabled-workflows` runs `get-enabled-workflows.yml` first. Downstream jobs use `needs: dashboard-enabled-workflows` and gate on its outputs:

- `effective-raw` empty (no open dashboard issue) → every registry id is treated as enabled for jobs that check `enabled-workflows`.
- `effective-raw` non-empty and the normalized `enabled-workflows` array is `[]` → no gated jobs run.
- Non-empty `enabled-workflows` → only listed registry ids pass the `contains(..., '<id>')` checks. Bare workflow ids are not accepted.

Jobs that do not list `needs: dashboard-enabled-workflows` are not gated this way (see [Internal ingress jobs](#internal-ingress-jobs-not-in-workflow-registryjson)).

Canonical registry ids and metadata live in `workflow-registry.json` at the repository root. Each subsection below pairs one registry entry with its ingress job(s).

## Routed workflows (`workflow-registry.json`)

The following subsections follow the order of entries in `workflow-registry.json`. Each subsection lists the registry fields and the ingress job(s) that honor that id in `enabled-workflows`. Where a dedicated routing document exists under `docs/routing/`, the subsection includes a **Routing** link to it (labels, triggers, and dispatch detail).

### Agent suggestions (registry id `agent-suggestions`)

| Registry field | Value |
|----------------|--------|
| `id` | `agent-suggestions` |
| `name` | Agent Suggestions |
| `description` | Suggests agentic workflows and improvements for the repository based on analysis of current setup. |

| Ingress job | Reusable workflow | Triggers (from `.github/workflows/oblt-aw-ingress.yml`) | Dashboard gate |
|-------------|-------------------|--------------------------------------------------------|----------------|
| `agent-suggestions` | `gh-aw-agent-suggestions.yml` | `schedule` | Yes — `enabled-workflows` must contain `agent-suggestions` when `effective-raw` is non-empty |

### Automated documentation (registry id `autodoc`)

| Registry field | Value |
|----------------|--------|
| `id` | `autodoc` |
| `name` | Automated Documentation |
| `description` | Analyzes documentation for gaps, outdated content, and inconsistencies; creates issues and PRs to improve docs. |

| Ingress job | Reusable workflow | Triggers | Dashboard gate |
|-------------|-------------------|----------|----------------|
| `autodoc` | `gh-aw-autodoc.yml` | `schedule` | Yes — `autodoc` |

### Automerge (registry id `automerge`)

| Registry field | Value |
|----------------|--------|
| `id` | `automerge` |
| `name` | Automerge |
| `description` | Enables auto-merge for approved dependency-update PRs that meet merge-ready criteria. |

| Ingress job | Reusable workflow | Triggers | Dashboard gate |
|-------------|-------------------|----------|----------------|
| `automerge` | `gh-aw-automerge.yml` | `schedule`; or `pull_request` `opened` / `synchronize` / `reopened` where `github.event.pull_request.user.login` is `elastic-vault-github-plugin-prod[bot]`; or `pull_request_review` `submitted` with `review.state == approved` for the same bot | Yes — `automerge` |

### Dependency review (registry id `dependency-review`)

**Routing:** [Dependency review routing](../routing/dependency-review-routing.md)

| Registry field | Value |
|----------------|--------|
| `id` | `dependency-review` |
| `name` | Dependency Review |
| `description` | Analyzes dependency-update PRs from bots, applies merge-ready labels when criteria are met. |

| Ingress job | Reusable workflow | Triggers | Dashboard gate |
|-------------|-------------------|----------|----------------|
| `dependency-review` | `gh-aw-dependency-review.yml` | `pull_request` `opened` / `synchronize` / `reopened`; author is one of `dependabot[bot]`, `renovate[bot]`, `Dependabot`, `Renovate`, `elastic-vault-github-plugin-prod[bot]` | Yes — `dependency-review` |

This job is separate from registry id `security`: it is PR-time dependency and license review for bot PRs, not the static repo-wide security scan. See `docs/workflows/gh-aw-dependency-review.md` and `docs/workflows/security-scanning-ruleset.md` (complementary workflows SEC-033–SEC-035).

### Duplicate issue detector (registry id `duplicate-issue-detector`)

| Registry field | Value |
|----------------|--------|
| `id` | `duplicate-issue-detector` |
| `name` | Duplicate Issue Detector |
| `description` | Detects potential duplicate issues when a new issue is opened or when the entrypoint is run manually. |

| Ingress job | Reusable workflow | Triggers | Dashboard gate |
|-------------|-------------------|----------|----------------|
| `duplicate-issue-detector` | `gh-aw-duplicate-issue-detector.yml` | `issues` `opened`, or `workflow_dispatch` | Yes — `duplicate-issue-detector` |

### Issue triage (registry id `issue-triage`)

| Registry field | Value |
|----------------|--------|
| `id` | `issue-triage` |
| `name` | Issue Triage |
| `description` | Triages newly opened issues using the generic issue-triage agentic workflow. |

| Ingress job | Reusable workflow | Triggers | Dashboard gate |
|-------------|-------------------|----------|----------------|
| `issue-triage` | `gh-aw-issue-triage.yml` | `issues` `opened` | Yes — `issue-triage` |

### Security (registry id `security`)

**Routing:** [Security routing](../routing/security-routing.md)

| Registry field | Value |
|----------------|--------|
| `id` | `security` |
| `name` | Security |
| `description` | Runs static security checks on workflows, shell scripts, and dependency manifests per the security scanning ruleset; opens issues for findings. |

There is one registry id for the whole security pipeline. The Control Plane Dashboard uses that id for the Security checkbox; `enabled-workflows` lists `security` when consumers restrict runs.

| Ingress job | Reusable workflow | Triggers | Dashboard gate |
|-------------|-------------------|----------|----------------|
| `security-detector` | `gh-aw-security-detector.yml` | `schedule`, `workflow_dispatch` | Yes — `security` |
| `security-triage` | `gh-aw-security-triage.yml` | `issues` `opened` with label `oblt-aw/detector/security`, or `issues` `labeled` with that label | Yes — `security` |
| `security-fixer` | `gh-aw-security-fixer.yml` | `issues` `labeled` with `oblt-aw/ai/fix-ready` and a `oblt-aw/triage/security-*` label | Yes — `security` |

Further reading:

- `docs/architecture/security-agent-architecture.md`
- `docs/workflows/gh-aw-security-detector.md`
- `docs/workflows/gh-aw-security-triage.md`
- `docs/workflows/gh-aw-security-fixer.md`

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
| `resource-not-accessible-by-integration-detector` | `gh-aw-resource-not-accessible-by-integration-detector.yml` | `schedule` | Yes — `resource-not-accessible-by-integration` |
| `resource-not-accessible-by-integration-triage` | `gh-aw-resource-not-accessible-by-integration-triage.yml` | `issues` `opened` with `oblt-aw/detector/res-not-accessible-by-integration`, or `issues` `labeled` with that label | Yes — `resource-not-accessible-by-integration` |
| `resource-not-accessible-by-integration-fixer` | `gh-aw-resource-not-accessible-by-integration-fixer.yml` | `issues` `labeled` with `oblt-aw/ai/fix-ready` and `oblt-aw/triage/res-not-accessible-by-integration` | Yes — `resource-not-accessible-by-integration` |

## Internal ingress jobs (not in `workflow-registry.json`)

These jobs exist only in `.github/workflows/oblt-aw-ingress.yml` and do not have registry ids:

| Job | Role |
|-----|------|
| `dashboard-enabled-workflows` | Invokes `get-enabled-workflows.yml`; supplies `effective-raw` and `enabled-workflows` to gated jobs. |
| `unsupported-trigger` | Runs when the event is not one of the supported combinations; fails the workflow with a clear message. It has no `needs: dashboard-enabled-workflows` and does not read the registry. |

## Configuration

Top-level permissions:

- `actions: read`
- `contents: write`
- `discussions: write`
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

- `workflow-registry.json` (canonical workflow ids for the Control Plane Dashboard)
- [Routing documentation index](../routing/README.md)
- [Dependency review routing](../routing/dependency-review-routing.md)
- [Security routing](../routing/security-routing.md)
- [Resource not accessible by integration routing](../routing/resource-not-accessible-by-integration-routing.md)

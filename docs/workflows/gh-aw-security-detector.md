# Workflow: `gh-aw-security-detector.yml`

## Overview

Source file: [.github/workflows/gh-aw-security-detector.yml](../../.github/workflows/gh-aw-security-detector.yml)

This reusable workflow scans the **calling repository** (consumer of oblt-aw ingress) for security issues in shell scripts, workflow YAML, and—when tooling is available—dependency manifests. It implements the detector stage of the pipeline in [docs/architecture/security-agent-architecture.md](../architecture/security-agent-architecture.md).

Triage and fixer stages use **`gh-aw-issue-triage.lock.yml`** and **`gh-aw-issue-fixer.lock.yml`** from [elastic/ai-github-actions](https://github.com/elastic/ai-github-actions); this workflow does **not** clone that repository.

Unlike the resource-not-accessible detector (workflow logs via `gh-aw-log-searching-agent`), the security detector runs **static checks** aligned with [docs/workflows/security-scanning-ruleset.md](security-scanning-ruleset.md) (SEC-001–SEC-044) and [elastic/observability-robots#3758](https://github.com/elastic/observability-robots/issues/3758): injection, secret management, supply chain, and least privilege.

## Prerequisites

- Triggered via `workflow_call` (for example from a caller that uses `schedule`).
- No repository secrets are required: issue creation uses the job’s default `GITHUB_TOKEN` (`issues: write`), and **`elastic/oblt-aw`** is checked out without a PAT (public repository).

## Usage

Single job **scan**:

1. Checks out the **calling** repository into `target/` (the consumer workspace to scan).
2. Checks out **[elastic/oblt-aw](https://github.com/elastic/oblt-aw)** at ref `main` into `_oblt-aw/` so host scripts exist on the runner; detector scripts are not copied into consumer repos.
3. Installs **shellcheck**, **jq**, **curl**, **pip**, **actionlint** (pinned via upstream download script), **zizmor**, and **semgrep** (registry rules downloaded on first use).
4. Optionally uses **actions/setup-node** when `target/**/package-lock.json` exists so **npm audit** can run for SEC-033.
5. Runs `_oblt-aw/scripts/security-scan.sh` with argument `target`, which emits findings as `file|line|rule|severity|message` (actionlint + zizmor + semgrep + shellcheck + custom heuristics + npm audit, with per-file/line deduplication).
6. Runs `_oblt-aw/scripts/create-security-issues.sh` to open issues with label `oblt-aw/detector/security` and title prefix `[oblt-aw][security]` in **the caller** (`github.repository`).

Detector scripts are always taken from the public repository **`elastic/oblt-aw`** at ref **`main`** (no checkout token). Scheduled callers do not need a `workflow_call` input for the host ref.

**Consumer example**:

```yaml
jobs:
  security-detector:
    uses: elastic/oblt-aw/.github/workflows/gh-aw-security-detector.yml@v1.0.0
```

## Scan logic (summary)

| Rules | Mechanism |
|-------|-----------|
| SEC-002, SEC-021, SEC-030, SEC-040, SEC-043, and other workflow rules | **zizmor** (offline audits; `ident` mapped to SEC IDs in [scripts/security-scan.sh](../../scripts/security-scan.sh)) |
| SEC-010, SEC-002 (expression), SEC-020 (credentials) | **actionlint** JSON output (security-related kinds / messages only) |
| SEC-010, SEC-012 | **semgrep** `p/github-actions` on `.github/workflows` |
| SEC-011 | shellcheck on `*.sh` / `*.bash`; actionlint also runs shellcheck on embedded `run:` scripts |
| SEC-032 | curl/wget in scripts without checksum/signature helpers in-file (custom heuristic) |
| SEC-033 | `npm audit` when lockfile + npm available |

Findings from multiple tools are **deduplicated** by `file|line`, keeping the highest severity. **gh-aw-dependency-review** (ingress) complements SEC-033–SEC-035 at PR time.

Additional rules in the ruleset may be added to the scripts over time.

## Configuration

- **Workflow-level** `permissions`: read-only — `actions: read`, `contents: read`, `issues: read`, `pull-requests: read`.
- **Job `scan` `permissions`**: adds `issues: write` for `GITHUB_TOKEN` (least privilege on the job that can open issues). The **Create issues from findings** step sets `GH_TOKEN` to **`github.token`** so `gh issue create` uses the same token (avoids enterprise policy blocks on long-lived fine-grained PATs).

## API / Interface

`workflow_call` contract:

- No `secrets` are declared; callers do not pass `COPILOT_GITHUB_TOKEN` for this workflow.

Callers that trigger on a **schedule** cannot rely on `workflow_call` inputs for the host script ref; this workflow always clones detector scripts from **[elastic/oblt-aw](https://github.com/elastic/oblt-aw)** at **`main`**.

## References

- Ingress routing: [docs/workflows/oblt-aw-ingress.md](oblt-aw-ingress.md) — workflow id `security` in [workflow-registry.json](../../workflow-registry.json)
- [Security agent architecture](../architecture/security-agent-architecture.md)
- [Security scanning ruleset](security-scanning-ruleset.md)
- [elastic/observability-robots#3758](https://github.com/elastic/observability-robots/issues/3758)

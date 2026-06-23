# Workflow: `oblt-aw-security-detector.yml`

## Overview

Source file: [.github/workflows/oblt-aw-security-detector.yml](../../.github/workflows/oblt-aw-security-detector.yml)

This reusable workflow scans the **calling repository** (consumer of oblt-aw ingress) for security issues in shell scripts, workflow YAML, and—when tooling is available—dependency manifests. It implements the detector stage of the pipeline in [docs/architecture/security-agent-architecture.md](../architecture/security-agent-architecture.md).

Triage and fixer stages use **`gh-aw-issue-triage.lock.yml`** and **`gh-aw-issue-fixer.lock.yml`** from [elastic/ai-github-actions](https://github.com/elastic/ai-github-actions); this workflow does **not** clone that repository.

Unlike the resource-not-accessible detector (workflow logs via `oblt-aw-log-searching-agent`), the security detector runs **static checks** aligned with [docs/workflows/security-scanning-ruleset.md](security-scanning-ruleset.md) and [elastic/observability-robots#3758](https://github.com/elastic/observability-robots/issues/3758): injection, secret management, supply chain, and least privilege. The current implementation emits findings for **SEC-002**, **SEC-010–SEC-012**, **SEC-020–SEC-022**, **SEC-030–SEC-033**, **SEC-035**, **SEC-040**, **SEC-042**, and **SEC-043**. See the ruleset traceability table for per-rule implementation mapping.

## Prerequisites

- Triggered via `workflow_call` (for example from a caller that uses `schedule`).
- No repository secrets are required: issue creation uses an **ephemeral GitHub token** from [`elastic/oblt-actions/github/create-token@v1`](https://github.com/elastic/oblt-actions/tree/v1/github/create-token) (so downstream workflows can run on issue events; `GITHUB_TOKEN` does not trigger them). **`elastic/oblt-aw`** is checked out without a PAT (public repository).

## Usage

Single job **scan**:

1. Checks out the **calling** repository into `target/` (the consumer workspace to scan).
2. Checks out **[elastic/oblt-aw](https://github.com/elastic/oblt-aw)** at ref `main` into `_oblt-aw/` so host scripts exist on the runner; detector scripts are not copied into consumer repos.
3. Installs **shellcheck**, **jq**, **curl**, **pip**, **actionlint** (pinned via upstream download script), **zizmor**, and **semgrep** (registry rules downloaded on first use).
4. Optionally uses **actions/setup-node** when `target/**/package-lock.json` exists so **npm audit** can run for SEC-033.
5. Runs `_oblt-aw/scripts/obs/security-scan.sh` with argument `target`, which emits findings as `file|line|rule|severity|message` (actionlint + zizmor + semgrep + shellcheck + custom heuristics + npm audit, with per-file/line deduplication).
6. When there are findings, creates an ephemeral token then runs `_oblt-aw/scripts/obs/create-security-issues.sh` to open issues in **the caller** (`github.repository`) with label `oblt-aw/detector/security`. Findings are **grouped by rule (SEC id)**: **one issue per rule** per run, not one issue per line. The issue **title** is `[oblt-aw][security] <SEC-xxx> — findings (<YYYY-MM-DD>)`, where the date is the analysis date (UTC calendar day; the workflow sets `SECURITY_SCAN_DATE` when creating issues). The **body** lists every occurrence for that rule (file, line, severity, message). The current issue-creation step does **not** emit `oblt-aw/severity/*` labels; severity is represented in the issue body and mapped in [Security Scanning Ruleset → Severity Levels](security-scanning-ruleset.md#severity-levels).

Each new issue triggers the **issues** event orchestrator. When `obs:security` is enabled, [oblt-aw-security-issue-superseder.yml](../../.github/workflows/oblt-aw-security-issue-superseder.yml) runs [`supersede-security-issues.sh`](../../scripts/obs/supersede-security-issues.sh) to close older open issues for the same SEC id before triage proceeds on the canonical issue. See [oblt-aw-security-issue-superseder.md](oblt-aw-security-issue-superseder.md).

Detector scripts are always taken from the public repository **`elastic/oblt-aw`** at ref **`main`** (no checkout token). Scheduled callers do not need a `workflow_call` input for the host ref.

**Consumer example**:

```yaml
jobs:
  security-detector:
    uses: elastic/oblt-aw/.github/workflows/oblt-aw-security-detector.yml@v1.0.0
```

## Scan logic (summary)

| Rules | Mechanism |
|-------|-----------|
| SEC-002, SEC-021, SEC-030, SEC-040, SEC-043, and other workflow rules | **zizmor** (offline audits; `ident` mapped to SEC IDs in [scripts/obs/security-scan.sh](../../scripts/obs/security-scan.sh)) |
| SEC-010, SEC-002 (expression), SEC-020 (credentials) | **actionlint** JSON output (security-related kinds / messages only) |
| SEC-010, SEC-012 | **semgrep** `p/github-actions` on `.github/workflows` |
| SEC-011 | shellcheck on `*.sh` / `*.bash`; actionlint also runs shellcheck on embedded `run:` scripts |
| SEC-032 | curl/wget in scripts without checksum/signature helpers in-file (custom heuristic) |
| SEC-033 | `npm audit` when lockfile + npm available |

Findings from multiple tools are **deduplicated** by `file|line`, keeping the highest severity. **gh-aw-dependency-review** (ingress) complements SEC-033–SEC-035 at PR time.

Additional rules in the ruleset may be added to the scripts over time.

## Configuration

- **Workflow-level** `permissions`: **`contents: read`** only.
- **Job `scan` `permissions`**: `actions: read`, `contents: read`, `pull-requests: read`, and **`id-token: write`** (for OIDC used by `create-token`). Issue creation does **not** use `GITHUB_TOKEN`; the **Create issues from findings** step sets `GH_TOKEN` to the ephemeral token from **Create ephemeral GitHub token**.
- **Call chain**: The distributed client template `trigger-oblt-aw-security-detector.yml` grants **`id-token: write`** on the `run-aw` job so the nested `scan` job can call `create-token`.

## API / Interface

`workflow_call` contract:

- No `secrets` are declared.

Callers that trigger on a **schedule** cannot rely on `workflow_call` inputs for the host script ref; this workflow always clones detector scripts from **[elastic/oblt-aw](https://github.com/elastic/oblt-aw)** at **`main`**.

## References

- Client template: [oblt-aw-client-template.md](oblt-aw-client-template.md) — registry id `security`
- [Security agent architecture](../architecture/security-agent-architecture.md)
- [Security scanning ruleset](security-scanning-ruleset.md)
- [Security issue superseder](oblt-aw-security-issue-superseder.md)
- [elastic/observability-robots#3758](https://github.com/elastic/observability-robots/issues/3758)

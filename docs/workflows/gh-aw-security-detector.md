# Workflow: `gh-aw-security-detector.yml`

## Overview

Source file: `.github/workflows/gh-aw-security-detector.yml`

This reusable workflow scans the **calling repository** (consumer of oblt-aw ingress) for security issues in shell scripts, workflow YAML, and—when tooling is available—dependency manifests. It implements the detector stage of the pipeline in `docs/architecture/security-agent-architecture.md`.

Triage and fixer stages use **`gh-aw-issue-triage.lock.yml`** and **`gh-aw-issue-fixer.lock.yml`** from `elastic/ai-github-actions`; this workflow does **not** clone that repository.

Unlike the resource-not-accessible detector (workflow logs via `gh-aw-log-searching-agent`), the security detector runs **static checks** aligned with `docs/workflows/security-scanning-ruleset.md` (SEC-001–SEC-044) and [elastic/observability-robots#3758](https://github.com/elastic/observability-robots/issues/3758): injection, secret management, supply chain, and least privilege.

## Prerequisites

- Triggered via `workflow_call`.
- Required secret: `COPILOT_GITHUB_TOKEN`.

## Usage

Single job **scan**:

1. Checks out the **calling** repository into `target/` (the consumer workspace to scan).
2. Checks out **`elastic/oblt-aw`** at ref `oblt-aw-ref` (default `main`) into `_oblt-aw/` so host scripts exist on the runner; detector scripts are not copied into consumer repos.
3. Installs **shellcheck** and **jq**.
4. Optionally uses **actions/setup-node** when `target/**/package-lock.json` exists so **npm audit** can run for SEC-033.
5. Runs `_oblt-aw/.github/scripts/security-scan.sh` with argument `target`, which emits findings as `file|line|rule|severity|message`.
6. Runs `_oblt-aw/.github/scripts/create-security-issues.sh` to open issues with label `oblt-aw/detector/security` and title prefix `[oblt-aw][security]` in **the caller** (`github.repository`).

## Host ref (`oblt-aw-ref`)

In reusable workflows, `github.*` refers to the **caller**; there is no reliable way to infer the `elastic/oblt-aw` commit pinned on the `uses:` line. Pass **`oblt-aw-ref`** with the same ref you use in `uses: elastic/oblt-aw/.github/workflows/gh-aw-security-detector.yml@<ref>` (for example `main` or a release tag). The default `main` matches callers that pin `@main`.

The **oblt-aw** checkout uses `COPILOT_GITHUB_TOKEN` so private repositories can be cloned when needed.

**Consumer example** (pin the workflow and pass the same ref for scripts):

```yaml
jobs:
  security-detector:
    uses: elastic/oblt-aw/.github/workflows/gh-aw-security-detector.yml@v1.0.0
    with:
      oblt-aw-ref: v1.0.0
    secrets:
      COPILOT_GITHUB_TOKEN: ${{ secrets.COPILOT_GITHUB_TOKEN }}
```

If you use `...@main`, you can omit `with.oblt-aw-ref` (default `main`).

## Scan logic (summary)

| Rules | Mechanism |
|-------|-----------|
| SEC-001–003, SEC-021 | Workflow grep patterns for secrets / logging |
| SEC-010 | `github.event.` usage in workflows |
| SEC-011 | shellcheck on `*.sh` / `*.bash` |
| SEC-030 | `uses:` refs not pinned to 40-char SHA (heuristic) |
| SEC-032 | curl/wget in scripts without checksum/signature helpers in-file |
| SEC-033 | `npm audit` when lockfile + npm available |
| SEC-040 | Broad `permissions` / `write` usage (heuristic) |
| SEC-043 | `pull_request_target` presence |

Additional rules in the ruleset may be added to the scripts over time. **gh-aw-dependency-review** (ingress) complements SEC-033–SEC-035 at PR time.

## Configuration

Permissions:

- `actions: read`
- `contents: read`
- `issues: write`
- `pull-requests: read`

## API / Interface

`workflow_call` contract:

- Input: `oblt-aw-ref` (`string`, optional, default `main`) — ref of `elastic/oblt-aw` to clone for detector scripts.
- Secret: `COPILOT_GITHUB_TOKEN` (`required: true`)

## References

- [Security agent architecture](../architecture/security-agent-architecture.md)
- [Security scanning ruleset](security-scanning-ruleset.md)
- [elastic/observability-robots#3758](https://github.com/elastic/observability-robots/issues/3758)

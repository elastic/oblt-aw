# Security category detectors

## Overview

The security workflow exposes four independently toggleable **category detectors** on the Control Plane Dashboard. Each runs the same static scan toolchain but emits findings only for rules in that category (see [security-scanning-ruleset.md](security-scanning-ruleset.md)).

| Sub-feature id | Workflow file | SEC rule focus |
|----------------|---------------|----------------|
| `injection` | [oblt-aw-security-injection-detector.yml](../../.github/workflows/oblt-aw-security-injection-detector.yml) | SEC-010–SEC-012 |
| `supply-chain` | [oblt-aw-security-supply-chain-detector.yml](../../.github/workflows/oblt-aw-security-supply-chain-detector.yml) | SEC-030–SEC-035 |
| `secrets` | [oblt-aw-security-secrets-detector.yml](../../.github/workflows/oblt-aw-security-secrets-detector.yml) | SEC-001–SEC-003, SEC-020–SEC-022 |
| `least-privilege` | [oblt-aw-security-least-privilege-detector.yml](../../.github/workflows/oblt-aw-security-least-privilege-detector.yml) | SEC-040–SEC-044 |

**Parent** checkbox `obs:security` gates triage, fixer, and superseder. Each category detector additionally requires its sub-feature id (`obs:security:injection`, etc.) in `enabled-workflows`.

This implements the detector stage of the pipeline in [docs/architecture/security-agent-architecture.md](../architecture/security-agent-architecture.md). Triage and fixer use **`gh-aw-issue-triage.lock.yml`** and **`gh-aw-issue-fixer.lock.yml`** from [elastic/ai-github-actions](https://github.com/elastic/ai-github-actions).

## Prerequisites

- Triggered via `workflow_call` from [oblt-aw-event-schedule.yml](../../.github/workflows/oblt-aw-event-schedule.yml) on `schedule` or `workflow_dispatch`.
- No repository secrets: issue creation uses an ephemeral token from [`elastic/oblt-actions/github/create-token@v1`](https://github.com/elastic/oblt-actions/tree/v1/github/create-token).

## Usage

Each category detector runs a single **scan** job:

1. Checks out the **calling** repository into `target/`.
2. Checks out **[elastic/oblt-aw](https://github.com/elastic/oblt-aw)** at ref `main` into `_oblt-aw/`.
3. Installs detector tools via `install_security_detector_tools.sh`.
4. Runs `_oblt-aw/scripts/obs/security-scan.sh target <category>` where `<category>` is `injection`, `supply-chain`, `secrets`, or `least-privilege`.
5. When findings exist, creates issues with label `oblt-aw/detector/security` via `create-security-issues.sh`.

New issues trigger the issues orchestrator; when `obs:security` is enabled, [oblt-aw-security-issue-superseder.yml](../../.github/workflows/oblt-aw-security-issue-superseder.yml) deduplicates open issues per SEC id before triage.

## Scan logic (summary)

Category filtering is applied after tool runs and deduplication in [scripts/obs/security-scan.sh](../../scripts/obs/security-scan.sh). Tools (actionlint, zizmor, semgrep, shellcheck, npm audit, custom heuristics) still execute fully; output is filtered to the requested category.

| Category | Example rules | Mechanisms |
|----------|---------------|------------|
| injection | SEC-010–SEC-012 | actionlint, zizmor, semgrep, shellcheck |
| secrets | SEC-002, SEC-020–SEC-022 | actionlint, zizmor |
| supply-chain | SEC-030–SEC-033, SEC-035 | zizmor, npm audit, curl/wget heuristic |
| least-privilege | SEC-040, SEC-042–SEC-043 | zizmor |

## Configuration

- Workflow-level `permissions`: `contents: read`.
- Job `scan` permissions: `actions: read`, `contents: read`, `pull-requests: read`, `id-token: write`.
- Client `trigger-oblt-aw-schedule.yml` must grant `id-token: write` on the schedule orchestrator job.

## References

- [Security routing](../routing/security-routing.md)
- [Security agent architecture](../architecture/security-agent-architecture.md)
- [Security scanning ruleset](security-scanning-ruleset.md)
- [Security issue superseder](oblt-aw-security-issue-superseder.md)

# Security Routing

## Overview

Client templates: `trigger-obs-aw-security-*.yml` → matching `obs-aw-security-*.yml`

Routed workflows (`obs-aw-security-*`; registry id `security`):

- [.github/workflows/obs-aw-security-injection-detector.yml](../../.github/workflows/obs-aw-security-injection-detector.yml)
- [.github/workflows/obs-aw-security-supply-chain-detector.yml](../../.github/workflows/obs-aw-security-supply-chain-detector.yml)
- [.github/workflows/obs-aw-security-secrets-detector.yml](../../.github/workflows/obs-aw-security-secrets-detector.yml)
- [.github/workflows/obs-aw-security-least-privilege-detector.yml](../../.github/workflows/obs-aw-security-least-privilege-detector.yml)
- [.github/workflows/obs-aw-security-issue-superseder.yml](../../.github/workflows/obs-aw-security-issue-superseder.yml)
- [.github/workflows/obs-aw-security-triage.yml](../../.github/workflows/obs-aw-security-triage.yml)
- [.github/workflows/obs-aw-security-fixer.yml](../../.github/workflows/obs-aw-security-fixer.yml)

All workflows use the same Control Plane dashboard gate: prelude allows `obs:security` when the parent workflow is enabled. Category detectors additionally require their sub-feature id (`obs:security:injection`, `obs:security:supply-chain`, `obs:security:secrets`, or `obs:security:least-privilege`) in `enabled-workflows` ([aw-prelude](../workflows/aw-prelude.md)).

## Usage

Routing rules in `obs-aw-security-*.yml` (issue routes follow the same label pattern as `resource-not-accessible-by-integration-*`):

- **Detector** — `schedule` or `workflow_dispatch`.
- **Superseder** — `issues` + `opened` when the issue has `oblt-aw/detector/security` (closes older open issues for the same SEC rule; see [docs/workflows/obs-aw-security-issue-superseder.md](../workflows/obs-aw-security-issue-superseder.md)).
- **Triage** — `issues` + `labeled` when the label applied is `oblt-aw/detector/security` (not on `opened`; create-with-label still emits `labeled`).
- **Fixer** — `issues` + `labeled` with `oblt-aw/ai/fix-ready`, and the issue has at least one label matching `oblt-aw/triage/security-*`.

Generic issue-triage and issue-fixer skip issues that carry security detector or triage labels so they do not compete with this pipeline.

## Trigger Conditions

### Detector

- **Events**: `schedule`, `workflow_dispatch`
- **Role**: Static scan of the repository by security category; opens issues with label `oblt-aw/detector/security` for findings. Four category detectors run independently when their sub-feature checkbox is enabled (see [docs/workflows/obs-aw-security-detector.md](../workflows/obs-aw-security-detector.md)).

### Superseder

- **Event**: `issues`
- **Action**: `opened`
- **Required label**: `oblt-aw/detector/security` on the **new** (canonical) issue
- **Role**: Closes older open detector issues for the same SEC id; skips issues with `oblt-aw/keep-open` or any open linked PR ([docs/workflows/obs-aw-security-issue-superseder.md](../workflows/obs-aw-security-issue-superseder.md)).

### Triage

- **Event**: `issues`
- **Action**: `labeled`
- **Required label**: `github.event.label.name == 'oblt-aw/detector/security'`
- **Filter**: The triage workflow has its own `target-repositories` filter; default `[]` allows all repositories.

### Fixer

- **Event**: `issues`
- **Action**: `labeled`
- **Required labels**:
  - `oblt-aw/ai/fix-ready` (the label that triggered the event)
  - At least one of: `oblt-aw/triage/security-injection`, `oblt-aw/triage/security-secrets`, `oblt-aw/triage/security-supply-chain`, `oblt-aw/triage/security-least-privilege`

The ingress uses `contains(join(github.event.issue.labels.*.name, ','), 'oblt-aw/triage/security-')` to match any security triage label.

## Labels

| Label | Purpose |
|-------|---------|
| `oblt-aw/triage/security-injection` | Expression, command, or YAML injection |
| `oblt-aw/triage/security-secrets` | Token/secret exposure, secrets in command strings |
| `oblt-aw/triage/security-supply-chain` | Action pinning, checksums, untrusted actions |
| `oblt-aw/triage/security-least-privilege` | Excessive permissions |
| `oblt-aw/ai/fix-ready` | Issue is ready for automated remediation |
| `oblt-aw/keep-open` | Superseder must not close this issue when a newer scan opens a replacement for the same SEC rule |

## Repository Filter

- **Triage/Fixer**: input `target-repositories` exists; default `[]` allows all; non-empty JSON array restricts to listed repositories.
- The workflows apply the filter internally via their `if` conditions.

## References

- [docs/workflows/obs-aw-security-detector.md](../workflows/obs-aw-security-detector.md)
- [docs/workflows/obs-aw-security-issue-superseder.md](../workflows/obs-aw-security-issue-superseder.md)
- [docs/workflows/obs-aw-security-triage.md](../workflows/obs-aw-security-triage.md)
- [docs/workflows/obs-aw-security-fixer.md](../workflows/obs-aw-security-fixer.md)

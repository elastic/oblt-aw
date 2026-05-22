# Security Routing

## Overview

Client templates: `oblt-aw-security-*.yml` → matching `oblt-aw-security-*.yml`

Routed workflows (`oblt-aw-security-*`; registry id `security`):

- [.github/workflows/oblt-aw-security-detector.yml](../../.github/workflows/oblt-aw-security-detector.yml)
- [.github/workflows/oblt-aw-security-triage.yml](../../.github/workflows/oblt-aw-security-triage.yml)
- [.github/workflows/oblt-aw-security-fixer.yml](../../.github/workflows/oblt-aw-security-fixer.yml)

All three workflows use the same Control Plane dashboard gate: prelude allows `obs:security` when [workflow-registry.json](../../config/obs/workflow-registry.json) id `security` is enabled ([aw-prelude](../workflows/aw-prelude.md)).

## Usage

Routing rules in `oblt-aw-security-*.yml` (issue routes follow the same label pattern as `resource-not-accessible-by-integration-*`):

- **Detector** — `schedule` or `workflow_dispatch`.
- **Triage** — `issues` + (`opened` and issue already has `oblt-aw/detector/security`) **or** (`labeled` and the label applied is `oblt-aw/detector/security`).
- **Fixer** — `issues` + `labeled` with `oblt-aw/ai/fix-ready`, and the issue has at least one label matching `oblt-aw/triage/security-*`.

## Trigger Conditions

### Detector

- **Events**: `schedule`, `workflow_dispatch`
- **Role**: Static scan of the repository; opens issues with label `oblt-aw/detector/security` for findings (see [docs/workflows/oblt-aw-security-detector.md](../workflows/oblt-aw-security-detector.md)).

### Triage

- **Event**: `issues`
- **Action**: `opened` (issue must include label `oblt-aw/detector/security`) **or** `labeled` (when `github.event.label.name == 'oblt-aw/detector/security'`)
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

## Repository Filter

- **Triage/Fixer**: input `target-repositories` exists; default `[]` allows all; non-empty JSON array restricts to listed repositories.
- The workflows apply the filter internally via their `if` conditions.

## References

- [docs/workflows/oblt-aw-security-detector.md](../workflows/oblt-aw-security-detector.md)
- [docs/workflows/oblt-aw-security-triage.md](../workflows/oblt-aw-security-triage.md)
- [docs/workflows/oblt-aw-security-fixer.md](../workflows/oblt-aw-security-fixer.md)

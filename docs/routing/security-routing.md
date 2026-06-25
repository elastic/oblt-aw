# Security Routing

## Overview

Client templates: `trigger-oblt-aw-security-*.yml` → matching `oblt-aw-security-*.yml`

Routed workflows (`oblt-aw-security-*`; registry id `security`):

- [.github/workflows/oblt-aw-security-detector.yml](../../.github/workflows/oblt-aw-security-detector.yml)
- [.github/workflows/oblt-aw-security-issue-superseder.yml](../../.github/workflows/oblt-aw-security-issue-superseder.yml)
- [.github/workflows/oblt-aw-security-triage.yml](../../.github/workflows/oblt-aw-security-triage.yml)
- [.github/workflows/oblt-aw-security-fixer.yml](../../.github/workflows/oblt-aw-security-fixer.yml)

All four workflows use the same Control Plane dashboard gate: prelude allows `obs:security` when [workflow-registry.json](../../config/obs/workflow-registry.json) id `security` is enabled ([aw-prelude](../workflows/aw-prelude.md)).

## Usage

Routing rules in `oblt-aw-security-*.yml` (issue routes follow the same label pattern as `resource-not-accessible-by-integration-*`):

- **Detector** — `schedule` or `workflow_dispatch`.
- **Superseder** — `issues` + `opened` when the issue has `oblt-aw/detector/security` (closes older open issues for the same SEC rule; see [docs/workflows/oblt-aw-security-issue-superseder.md](../workflows/oblt-aw-security-issue-superseder.md)).
- **Triage** — `issues` + (`opened` and issue already has `oblt-aw/detector/security`) **or** (`labeled` and the label applied is `oblt-aw/detector/security`).
- **Fixer** — `issues` + `labeled` with `oblt-aw/ai/fix-ready`, and the issue has at least one label matching `oblt-aw/triage/security-*`.

## Trigger Conditions

### Detector

- **Events**: `schedule`, `workflow_dispatch`
- **Role**: Static scan of the repository; opens issues with label `oblt-aw/detector/security` for findings (see [docs/workflows/oblt-aw-security-detector.md](../workflows/oblt-aw-security-detector.md)).

### Superseder

- **Event**: `issues`
- **Action**: `opened`
- **Required label**: `oblt-aw/detector/security` on the **new** (canonical) issue
- **Role**: Closes older open detector issues for the same SEC id; skips issues with `oblt-aw/keep-open` or any open linked PR ([docs/workflows/oblt-aw-security-issue-superseder.md](../workflows/oblt-aw-security-issue-superseder.md)).

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
| `oblt-aw/keep-open` | Superseder must not close this issue when a newer scan opens a replacement for the same SEC rule |

## Repository Filter

- **Triage/Fixer**: input `target-repositories` exists; default `[]` allows all; non-empty JSON array restricts to listed repositories.
- The workflows apply the filter internally via their `if` conditions.

## References

- [docs/workflows/oblt-aw-security-detector.md](../workflows/oblt-aw-security-detector.md)
- [docs/workflows/oblt-aw-security-issue-superseder.md](../workflows/oblt-aw-security-issue-superseder.md)
- [docs/workflows/oblt-aw-security-triage.md](../workflows/oblt-aw-security-triage.md)
- [docs/workflows/oblt-aw-security-fixer.md](../workflows/oblt-aw-security-fixer.md)

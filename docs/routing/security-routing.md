# Security Routing

## Overview

Entrypoint source: `.github/workflows/oblt-aw-ingress.yml`

Routed workflows:

- `.github/workflows/gh-aw-security-triage.yml`
- `.github/workflows/gh-aw-security-fixer.yml`

## Usage

Routing rules from ingress:

- `issues` + `opened` -> triage
- `issues` + `labeled` +
  - `github.event.label.name == 'oblt-aw/ai/fix-ready'`
  - issue contains at least one label matching `oblt-aw/triage/security-*`
  -> fixer

## Trigger Conditions

### Triage

- **Event**: `issues`
- **Action**: `opened`
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

- `docs/workflows/gh-aw-security-triage.md`
- `docs/workflows/gh-aw-security-fixer.md`

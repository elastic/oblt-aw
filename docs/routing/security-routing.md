# Security Routing

## Overview

Entrypoint source: `.github/workflows/oblt-aw-ingress.yml`

Routed workflows:

- `.github/workflows/gh-aw-security-triage.yml`
- `.github/workflows/gh-aw-security-fixer.yml`

These ingress routes use the same Control Plane dashboard gate as `gh-aw-security-detector.yml`: jobs run only when `workflow-registry.json` id `security` is enabled (see `docs/workflows/oblt-aw-ingress.md` — `get-enabled-workflows` / `enabled-workflows`).

## Usage

Routing rules from ingress (same pattern as `resource-not-accessible-by-integration-*` in `oblt-aw-ingress.yml`):

- **Triage** — `issues` + (`opened` and issue already has `oblt-aw/detector/security`) **or** (`labeled` and the label applied is `oblt-aw/detector/security`).
- **Fixer** — `issues` + `labeled` with `oblt-aw/ai/fix-ready`, and the issue has at least one label matching `oblt-aw/triage/security-*`.

## Trigger Conditions

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

- `docs/workflows/gh-aw-security-triage.md`
- `docs/workflows/gh-aw-security-fixer.md`

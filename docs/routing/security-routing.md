# Security Routing

## Overview

Entrypoint source: `.github/workflows/oblt-aw-ingress.yml`

Routed workflows:

- `.github/workflows/gh-aw-security-detector.yml`
- `.github/workflows/gh-aw-security-triage.yml`
- `.github/workflows/gh-aw-security-fixer.yml`

## Usage

Routing rules from ingress:

- `schedule` or `workflow_dispatch` -> detector
- `issues` + `opened` -> triage
- `issues` + `labeled` +
  - `github.event.label.name == 'oblt-aw/ai/fix-ready'`
  - issue contains any label matching `oblt-aw/triage/security-*`
  -> fixer

## Trigger Conditions

| Workflow | Trigger | Notes |
|----------|---------|-------|
| Detector | `schedule`, `workflow_dispatch` | Requires `COPILOT_GITHUB_TOKEN` |
| Triage | `issues` + `opened` | Runs on new security issues |
| Fixer | `issues` + `labeled` | Requires `oblt-aw/ai/fix-ready` and at least one `oblt-aw/triage/security-*` |

## Labels

### Triage labels (`oblt-aw/triage/security-*`)

- `oblt-aw/triage/security-injection`
- `oblt-aw/triage/security-secrets`
- `oblt-aw/triage/security-supply-chain`
- `oblt-aw/triage/security-least-privilege`
- `oblt-aw/triage/other`
- `oblt-aw/triage/needs-info`

### Fixer gate labels

- `oblt-aw/ai/fix-ready` — required for fixer to run
- Any `oblt-aw/triage/security-*` — required for fixer to run (issue must have both)

## Repository Filter Behavior

When called directly:

- **Detector**: Runs in each repository that invokes it (no filter). Receives `COPILOT_GITHUB_TOKEN` from ingress.
- **Triage**: Input `target-repositories` exists; default `[]` allows all; non-empty array restricts to listed repositories.
- **Fixer**: Input `target-repositories` exists; default `[]` allows all; non-empty array restricts to listed repositories.

## References

- `docs/workflows/gh-aw-security-detector.md`
- `docs/workflows/gh-aw-security-triage.md`
- `docs/workflows/gh-aw-security-fixer.md`

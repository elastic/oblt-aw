# Resource Not Accessible by Integration Routing

## Overview

Entrypoint source: `.github/workflows/oblt-aw-ingress.yml`

Routed workflows:

- `.github/workflows/gh-aw-resource-not-accessible-by-integration-detector.yml`
- `.github/workflows/gh-aw-resource-not-accessible-by-integration-triage.yml`
- `.github/workflows/gh-aw-resource-not-accessible-by-integration-fixer.yml`

## Usage

Routing rules from ingress:

- `schedule` or `workflow_dispatch` -> detector
- `issues` + `opened` -> triage
- `issues` + `labeled` +
  - `github.event.label.name == 'oblt-aw/ai/fix-ready'`
  - issue contains label `oblt-aw/triage/resource-not-accessible-by-integration`
  -> fixer

Repository filter behavior for detector/triage/fixer when called directly:

- input `target-repositories` exists on each workflow.
- default is `[]`.
- `[]` means allow all repositories.
- otherwise only repositories in the JSON array are allowed.

## References

- `docs/workflows/gh-aw-resource-not-accessible-by-integration-detector.md`
- `docs/workflows/gh-aw-resource-not-accessible-by-integration-triage.md`
- `docs/workflows/gh-aw-resource-not-accessible-by-integration-fixer.md`

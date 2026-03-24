# Resource Not Accessible by Integration Routing

## Overview

Entrypoint source: `.github/workflows/oblt-aw-ingress.yml`

Routed workflows:

- `.github/workflows/gh-aw-resource-not-accessible-by-integration-detector.yml`
- `.github/workflows/gh-aw-resource-not-accessible-by-integration-triage.yml`
- `.github/workflows/gh-aw-resource-not-accessible-by-integration-fixer.yml`

## Usage

Routing rules from ingress:

- `schedule` -> detector
- `issues` -> triage when:
  - `opened` and the issue already includes label `oblt-aw/detector/res-not-accessible-by-integration`, or
  - `labeled` and `github.event.label.name` is `oblt-aw/detector/res-not-accessible-by-integration`
  (The `opened` branch covers issues created with the detector label in the same request; GitHub does not emit `labeled` for labels set at creation.)
- `issues` + `labeled` +
  - `github.event.label.name == 'oblt-aw/ai/fix-ready'`
  - issue contains label `oblt-aw/triage/res-not-accessible-by-integration`
  -> fixer

Repository filter behavior when called directly:

- **Detector**: Runs in each repository that invokes it (no filter).
- **Triage/Fixer**: input `target-repositories` exists; default `[]` allows all; non-empty array restricts to listed repositories.

## References

- `docs/workflows/gh-aw-resource-not-accessible-by-integration-detector.md`
- `docs/workflows/gh-aw-resource-not-accessible-by-integration-triage.md`
- `docs/workflows/gh-aw-resource-not-accessible-by-integration-fixer.md`

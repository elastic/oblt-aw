# Resource Not Accessible by Integration Routing

## Overview

Client templates: `trigger-obs-aw-resource-not-accessible-by-integration-*.yml` → matching `obs-aw-*` workflows

Routed workflows:

- [.github/workflows/obs-aw-resource-not-accessible-by-integration-detector.yml](../../.github/workflows/obs-aw-resource-not-accessible-by-integration-detector.yml)
- [.github/workflows/obs-aw-resource-not-accessible-by-integration-triage.yml](../../.github/workflows/obs-aw-resource-not-accessible-by-integration-triage.yml)
- [.github/workflows/obs-aw-resource-not-accessible-by-integration-fixer.yml](../../.github/workflows/obs-aw-resource-not-accessible-by-integration-fixer.yml)

## Usage

Routing rules from ingress:

- `schedule` -> detector
- `issues` -> triage when:
  - `labeled` and `github.event.label.name` is `oblt-aw/detector/res-not-accessible-by-integration`
  (Triage does not run on `opened`; create-with-label still emits `labeled` for the detector label.)
- `issues` + `labeled` +
  - `github.event.label.name == 'oblt-aw/ai/fix-ready'`
  - issue contains label `oblt-aw/triage/res-not-accessible-by-integration`
  -> fixer

Generic issue-triage and issue-fixer skip issues that carry this detector or triage label so they do not compete with this pipeline.

All three routes (detector, triage, fixer) also require the shared dashboard gate to pass: `enabled-workflows` must contain `obs:resource-not-accessible-by-integration`.

For dashboard gate semantics (`get-enabled-workflows` and `enabled-workflows`), see [docs/workflows/aw-prelude.md](../workflows/aw-prelude.md).

When called directly, **detector**, **triage**, and **fixer** all run in the repository that invokes the reusable workflow (no extra repository allowlist).

## References

- [docs/workflows/obs-aw-resource-not-accessible-by-integration-detector.md](../workflows/obs-aw-resource-not-accessible-by-integration-detector.md)
- [docs/workflows/obs-aw-resource-not-accessible-by-integration-triage.md](../workflows/obs-aw-resource-not-accessible-by-integration-triage.md)
- [docs/workflows/obs-aw-resource-not-accessible-by-integration-fixer.md](../workflows/obs-aw-resource-not-accessible-by-integration-fixer.md)

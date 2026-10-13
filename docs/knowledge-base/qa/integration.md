---
navigation_title: Integration
description: Integration tests for wrapper, lock, and policy wiring without a live model.
applies_to: {}
---

# Integration

Proves wrapper ↔ lock ↔ token/policy/fragment wiring together without a live model (or with stubbed agent steps). Higher layers must not replace this one.

## Where it lives

- Tests: `tests/integration/`
- Fixtures: `testdata/agentic/` (per-workflow trees)

First slice: `tests/integration/test_estc_pr_buildkite_detective.py` with fixtures under `testdata/agentic/estc-pr-buildkite-detective/` ([#1910](https://github.com/elastic/oblt-aw/issues/1910)).

## Where it runs

Every PR via `python-tests` in [`ci.yml`](../../workflows/ci.md):

```bash
pytest tests/unit tests/integration -v --tb=short
```

Live `tests/e2e/` is excluded from that job.

## What it covers

- Compose wrapper inputs from fixtures that mimic `aw-resolve-agentic-assets` outputs
- Validate lock `workflow_call` inputs after fragment or interface changes
- Prefer recorded GitHub API fixtures over live calls when asserting orchestration scripts

Token-policy dry-run paths are deferred relative to the first ESTC slice.

**Assert:** wiring and contracts across modules. Agent model calls stay stubbed or skipped.

## See also

- Layer definitions: [Testing platform](../../architecture/agentic-workflow-testing-platform.md#layer-definitions)
- [QA overview](index.md)
- [E2E](e2e.md) — live path after integration contracts hold

---
navigation_title: Unit
description: Unit tests for deterministic framework logic in oblt-aw.
applies_to: {}
---

# Unit

Proves pure functions and scripts for known inputs and outputs. No live GitHub agent runs.

## Where it lives

- Python: `tests/unit/*.py`
- TypeScript: `tests/unit/*.test.ts`

## Where it runs

Every PR via [`ci.yml`](../../workflows/ci.md):

- `python-tests` — `pytest tests/unit tests/integration`
- `typescript-tests` — `npm test` → `tsx --test tests/unit/*.test.ts`

## What it covers (examples)

- Control Plane dashboard enablement and gate evaluation
- Instruction fragments and APM asset resolution
- Registry and org config
- Distribution helpers
- TypeScript helpers (for example automerge validation)

**Assert:** deterministic equality and typed errors.

## See also

- Layer definitions: [Testing platform](../../architecture/agentic-workflow-testing-platform.md#layer-definitions)
- [QA overview](index.md)

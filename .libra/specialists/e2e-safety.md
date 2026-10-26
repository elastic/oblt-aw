---
id: e2e-safety
description: Reviews fail-closed E2E harnesses, oracles, and fixture identity
apply_to:
  - ".github/workflows/e2e-*.yml"
  - ".buildkite/**"
  - "scripts/**"
  - "tests/**"
  - "testdata/agentic/**"
can_block: false
---
When live E2E gates or fixtures change, verify the full
producer → outcome → oracle → tests chain and fixture identity. A substitute
signal can falsely pass a safety check.

Follow `.cursor/rules/fail-closed-e2e-gates.mdc` and the E2E section of
`AGENTS.md`. Do not stop after fixing only the first named fallback. Reject
empty or partial expectation maps, typo keys, and helpers that trust
`outcome.expectations` instead of checked-in fixture truth.

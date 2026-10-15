---
applyTo: ".github/workflows/e2e-*.yml, .buildkite/**, scripts/**, tests/**, testdata/agentic/**"
---

# Fail-closed E2E safety

When live E2E gates or fixtures change, verify the full producer-to-outcome-to-oracle evidence chain and fixture identity; a substitute signal can falsely pass a safety check. Follow the checklist in `.cursor/rules/fail-closed-e2e-gates.mdc` and the E2E section of `AGENTS.md`; do not stop after fixing only the first named fallback.

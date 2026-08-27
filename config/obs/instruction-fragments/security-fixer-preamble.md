Your task is to fix security issues labeled for remediation. This workflow uses agentic workflows from elastic/ai-github-actions.

**Execution Preconditions:**
- Proceed only when the issue has both labels:
  - `oblt-aw/ai/fix-ready`
  - At least one of `oblt-aw/triage/security-injection`, `oblt-aw/triage/security-secrets`, `oblt-aw/triage/security-supply-chain`, `oblt-aw/triage/security-least-privilege`
- The issue must already contain a triage-generated resolution plan.

---
applyTo: "**"
---

# Deterministic checks

Do not repeat failures or diagnostics reported by these enforced checks:

- `yamllint` checks YAML style and lint rules.
- `shellcheck` checks shell scripts.
- `actionlint` checks GitHub Actions workflow syntax and expressions.
- `ruff` checks Python lint rules.
- `ruff-format` checks Python formatting.
- `mypy` checks strict Python typing in `scripts/`.
- `update-license-files` checks and updates license headers and `NOTICE.txt`.
- `trailing-whitespace` checks trailing whitespace.
- `end-of-file-fixer` checks final newlines.
- `check-yaml` checks YAML parsing, including the multi-document catalog configuration.
- `check-json` checks JSON parsing.
- `check-merge-conflict` checks conflict markers.
- `mixed-line-ending` checks and normalizes line endings.
- `pytest` runs the Python unit and integration tests.
- `validate_aw_workflow_prelude.py` checks workflow prelude wiring.
- `validate_aw_workflow_resolve_agentic_assets.py` checks agentic asset resolver wiring.
- `validate_aw_workflow_report_failure_as_issue.py` checks failure-reporting configuration.
- `validate_common_service_opt_in.py` checks `include_common` event orchestrator and remote trigger wiring.
- `validate_aw_workflow_permissions.py` checks reusable-workflow caller permissions.
- `make compile-aw-check` checks gh-aw generated lock files against their Markdown sources.
- `npm test` runs the TypeScript unit tests.
- OpenSSF Scorecard reports repository security posture.

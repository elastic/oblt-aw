# oblt-aw review instructions

oblt-aw is the Observability control plane for GitHub Agentic Workflows. Most
expensive mistakes are in workflow routing, permissions, fail-closed gates, and
client distribution—not ordinary application code.

Before commenting, read `.github/skills/code-review/SKILL.md` and apply it.
Libra also loads `AGENTS.md` from the default branch.

## Comment only when

- The PR introduces or worsens a concrete correctness, security, data-integrity,
  compatibility, reliability, rollout, or operability defect.
- Changed material behavior has no test that would catch a realistic regression.

Prioritize: (1) correctness / security / data integrity, (2) design problems with
a concrete consequence, (3) missing coverage for changed behavior.

## Stay silent when

- The issue is formatting, naming preference, import order, or anything
  Prettier, ruff, actionlint, mypy, yamllint, schema validators, or CI already
  report (see `.github/instructions/deterministic-checks.instructions.md`).
- The finding is praise, a summary, an optional refactor, or a speculative
  suggestion.
- The defect existed before this PR and the diff does not make it worse.

## Domain checks

- Workflow Markdown under `.github/workflows/` (including `gh-aw-fragments/`)
  must keep matching `.lock.yml` files in sync via `make compile-aw-check`. Do
  not hand-edit locks.
- Do not reintroduce a monolithic `oblt-aw.yml` or `oblt-aw-ingress.yml`. Client
  entrypoints live under `.github/remote-workflow-template/`.
- Fail-closed E2E: reject substitute signals (empty expectation maps, typo keys,
  trusting copied `outcome.expectations`, soft-skip cleanup as success). Walk
  producer → outcome → oracle → tests.
- Prefer leaf job names and never OR distinct jobs (approve ≠ merge).
- Permissions stay least privilege; flag broader token or secret scope without a
  concrete need.
- Do not treat pytest alone as a green merge gate when pre-commit (including
  actionlint/mypy) is required for the change.

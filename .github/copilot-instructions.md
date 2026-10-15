# oblt-aw Copilot guidance

oblt-aw is a shared framework and control plane for GitHub Agentic Workflows. Keep this file concise: shared PR review policy lives in `.github/instructions/review-policy-*.instructions.md`; use the path-scoped workflow, client-distribution, and E2E instructions for matching changes. Follow `.github/skills/code-review/SKILL.md` for the repository review checklist and `AGENTS.md` for implementation guardrails. CI tool versions are defined in `.github/workflows/ci.yml`.

Toolchain: GitHub Actions/gh-aw YAML, Python control-plane scripts, and TypeScript tests; CI versions are pinned in `.github/workflows/ci.yml`.

# High-signal code review policy

<!-- configure-ai-review:split-baseline:start -->
The bundled review baseline is intentionally split verbatim across `.github/instructions/review-policy-core.instructions.md`, `.github/instructions/review-policy-security.instructions.md`, and `.github/instructions/review-policy-tests.instructions.md` so each instruction file remains below Copilot's 4,000-character limit. Keep this index short; do not copy the full baseline back into it.
<!-- configure-ai-review:split-baseline:end -->

---
name: code-review
description: Use this skill when reviewing changes in oblt-aw, especially workflow routing, GitHub Actions configuration, control-plane logic, docs, and E2E safety checks.
---

# oblt-aw code review skill

Use this skill to review pull requests or local diffs in this repository with an emphasis on correctness, safety, and maintainability. This repo is the control plane for GitHub Agentic Workflows (`oblt-aw`): most meaningful risk is in workflow configuration, routing, permissions, and fail-closed gating rather than normal application code.

## Repository context

- Main workflow source: `.github/workflows/`
- Generated workflow locks: `.github/workflows/**/*.lock.yml`
- Shared gh-aw compile fragments: `.github/workflows/gh-aw-fragments/`
- Per-org client entrypoints: `.github/remote-workflow-template/`
- Org registry and enablement config: `config/<org>/`
- Shared validation and automation: `scripts/`
- Architecture and workflow docs: `docs/`
- E2E and harness tests: `tests/`
- Checked-in E2E fixture truth: `testdata/agentic/**/case.json`
- Safety rules and repo guardrails: `AGENTS.md`, `.cursor/rules/*.mdc`

## Review goals

Review for the issues that are most expensive to miss in this repo:

- workflow routing or trigger mistakes
- broken or drifted gh-aw compiled output
- fail-closed gate regressions that would green on a misleading signal
- over-broad permissions, token usage, or secret exposure
- incorrect workflow naming or nested job matching
- missing validation or documentation for changes
- changes that work locally but violate repository guardrails

## Always check before concluding

1. Start with the exact diff and intent of the change.
2. Read only the touched area first; expand to adjacent files only when the evidence requires it.
3. Verify any claim against code, workflow config, docs, or tests; do not rely on assumptions.
4. If the evidence is incomplete or ambiguous, prefer `noop` over a speculative review comment.
5. Re-read the output as a skeptical reviewer before submitting it.

## Repo-specific review checklist

### 1. Workflow and gh-aw correctness

- If a source file under `.github/workflows/*.md` changed, check whether generated `.lock.yml` files were regenerated and committed.
- For workflow-source edits, prefer `make compile-aw-check` as the authoritative validation step.
- Verify the source file and the compiled lock stay in sync; do not hand-edit lock files.
- Treat a workflow-source `.md` change without the matching generated `.lock.yml` update as a blocker until `make compile-aw-check` has been run and the drift resolved.
- Review for mislabeled job ids, wrong workflow routes, or trigger names that do not match the intended execution path.
- Prefer exact leaf job names and explicit job conclusions over broad substring matching.
- Reject changes that reintroduce a monolithic `oblt-aw.yml` or `oblt-aw-ingress.yml`; use the distributed client templates under `.github/remote-workflow-template/` instead.

### 2. Fail-closed review logic

This repo explicitly rejects substitute signals and false greens. Review for these common patterns:

- `conclusion` used where a named job conclusion is required
- empty or partial expectation maps that still allow a pass
- duplicated or broad OR logic across different jobs (`approve` vs `merge`)
- nested gating that accepts weak or missing evidence
- harness logic that trusts copied outcome blobs instead of checked-in fixture truth under `testdata/agentic/**/case.json`
- status contexts or routes that would pass on the wrong workflow or wrong branch

The repo guidance in `.cursor/rules/fail-closed-e2e-gates.mdc` is the baseline: if the named field is absent, empty, mistyped, or wrong, the gate should fail closed. For any harness, oracle, or gate change, walk the full evidence chain — producer → outcome → oracle → tests — and do not stop after the first named fallback you remove. If that chain is incomplete or still has substitute signals, treat it as a bug.

### 3. Permissions, secrets, and trust boundaries

- Look for risky patterns such as `pull_request_target`, broad write permissions, or secrets on paths that expose untrusted code.
- Check whether token policies, allow-lists, or permission scopes match the workflow purpose.
- For shared repos and automation, prefer minimal scope and explicit trust boundaries.
- If a workflow requests broader access than the task requires, call that out.
- For client workflow changes, confirm they stay within the distributed model described in `AGENTS.md` and do not blur org boundaries or trust untrusted code paths with extra privileges.

### 4. Control-plane and routing integrity

- Ensure shared prelude gating and allow lists still match the intended signals.
- Treat `.github/workflows/aw-prelude.yml` and `scripts/validate_aw_workflow_prelude.py` as the naming/routing contract for shared prelude behavior; mismatches there are blockers.
- Validate that route wrappers and org-specific client workflows align with the naming conventions documented in `AGENTS.md` and `docs/workflows/README.md`.
- Check that workflow enablement/registry changes match the repo's documented control-plane model.

### 5. Validation and CI discipline

For any touched files, the repo expects local validation before merge:

- `pre-commit run --files <touched-paths>`
- `pre-commit` includes `actionlint`, so workflow/YAML changes must not be waved through without that gate passing.
- for workflow markdown changes: `make compile-aw-check`
- apply the smallest relevant test command for the change, not a broad suite when a focused check is enough

Do not treat pytest alone as equivalent to a passing repo gate. Pre-commit and workflow validation are mandatory repository rules.

## Review output standards

Provide findings that are precise, actionable, and evidence-based.

Use this style:

- Finding: a concise description of the problem
- Evidence: exact file path and relevant lines or config block
- Why it matters: the business or safety impact
- Fix: a clear suggestion or next step

Prefer review comments like:

- "This workflow will still pass when the named job is absent because ..."
- "The compiled lock is now out of sync with the workflow source, which will fail `make compile-aw-check`."
- "This gate accepts a substitute signal instead of the required evidence and should fail closed."

## When to say no issue

Say no issues found only when the evidence actually supports that conclusion. If a change touches workflow routing, control-plane logic, secret scope, or E2E gate logic, do not dismiss a concern just because the diff is small.

If the review cannot be completed confidently, say so and request the missing evidence instead of guessing.

## Review posture

Be skeptical and precise.

- Silence is better than noise.
- A false positive is expensive.
- If you cannot verify it from the code, do not assert it.
- If a concern depends on speculation or missing context, `noop` is the correct output.

The point is not to find problems everywhere; it is to catch the meaningful regressions that would cost real engineering time or weaken the control-plane safety model.

<!-- configure-ai-review:baseline:start -->
# High-signal code review policy

These rules apply only when reviewing a pull request. They do not apply to Copilot Chat or cloud agent tasks. When reviewing, default to leaving no comment. Comment only when the changed code introduces a concrete correctness, security, data-integrity, compatibility, reliability, rollout, or operability defect, or when changed material behavior has no test that would catch a regression (see "Missing tests for material behavior" below).

When multiple issues compete for attention, prioritize in this order: (1) concrete correctness, security, or data-integrity defects; (2) architectural or design problems with a concrete, describable consequence; (3) missing test coverage for changed behavior. Leave the highest-priority comments first.

Do not comment on wording, spelling, formatting, naming preferences, syntax, style, import ordering, or other concerns that a compiler, formatter, linter, schema validator, test, or CI check enabled in this repository already reports. Do not restate a failing automated check. Do not leave praise, summaries, optional refactors, generic best practices, or speculative suggestions.

Before leaving a comment, verify all of the following:

- The issue is introduced or made materially worse by this pull request.
- You can describe a specific failure scenario and its impact.
- The finding starts from the changed lines. You may read callers, tests, and configuration to confirm it, but do not report issues the diff does not introduce or make worse.
- The repository's current code and configuration support the claim.
- The comment identifies the affected path and gives an actionable correction or asks for concrete missing evidence.
- The expected value of the comment is high enough to interrupt a human reviewer.

If any condition is missing, remain silent. Express uncertainty only when the uncertainty itself is a material risk that the author can resolve with specific evidence. On a re-review after new commits, do not repeat a comment on a line that has not changed since the prior run.

Use the repository's `.github/skills/code-review/SKILL.md` for domain-specific review checks when it exists. Copilot review is advisory. Whether its approval counts toward required approvals is controlled by org and branch settings, not this file.

## Trust-boundary and supply-chain changes

Always inspect a diff that changes CI, build, release, dependency, credential,
network, or security configuration. Note: Copilot code review does not inspect
lockfiles, `requirements.txt`, or generated files — leave those to Dependabot
and human review. Leave a review comment when the change introduces or materially
broadens a capability without a concrete, repository-supported need and an
appropriate control. In particular, flag:

- broader token, role, cloud, repository, or secret permissions than the changed
  operation requires;
- new collection, copying, logging, caching, artifact upload, or persistence of
  credentials or secret-bearing worker state;
- privileged workflows that check out, download, or execute untrusted pull-
  request code, artifacts, build scripts, hooks, or dependency lifecycle scripts;
- new outbound destinations, telemetry, uploads, remote shells, or network
  services unrelated to the repository's documented responsibility;
- downloaded or remotely referenced code, actions, reusable workflows, images,
  plugins, tools, or binaries that are executed without immutable identity and
  integrity verification;
- new dependencies or build inputs that are not resolved immutably;
- weakened or bypassed tests, approval gates, secret scanning, signature or
  checksum verification, TLS verification, sandboxing, or least-privilege
  defaults;
- shared caches, workspaces, or non-ephemeral runners that allow an untrusted or
  earlier build to influence a privileged or later build;
- unexplained executable binaries, encoded or obfuscated payloads, generated
  code without a documented generator, or functionality unrelated to the
  repository's stated purpose;
- untrusted input, such as a pull-request title, branch name, or issue body,
  placed directly into a `run:` script through a `${{ }}` expression instead
  of through an environment variable.

For GitHub Actions, require third-party actions and reusable workflows to be
pinned to a full commit SHA from the intended upstream repository. Require
container images by digest when they execute in CI, build, release, or
production paths. Require downloaded executables or scripts to be pinned to an
immutable version and verified before execution with an expected cryptographic
digest, or with a signature or attestation from an expected signer. HTTPS or a
checksum downloaded from the same mutable source is not sufficient integrity
evidence. Reject pipe-to-shell execution of unverified remote content.

For package-manager dependencies, require the repository's lockfile or equivalent
immutable resolution to be committed and enforced. Do not comment on a version
range merely because it is a range when an enforced lockfile pins the resolved
artifact. Do comment when a new executable build or runtime dependency can float
without reviewed immutable resolution.

Describe the exact new trust path, the realistic abuse or compromise scenario,
and the smallest corrective control. Do not allege malicious intent; when code
appears unrelated or concealed, ask for concrete purpose and provenance and
recommend removal when neither is established.

## Missing tests for material behavior

Check whether changed behavior has meaningful deterministic coverage. Comment
when the diff adds or changes a material correctness, security, compatibility,
failure-handling, state-transition, permission, parsing, retry, concurrency,
build, or release behavior and no existing or new test would fail if that
behavior regressed. A bug fix should normally include a regression test that
fails for the original defect.

Before commenting, inspect the relevant existing tests, including higher-level
and generated-output tests. Do not request tests for documentation-only changes,
mechanical refactors with unchanged behavior, generated files whose source and
generation are already tested, or behavior already exercised at an appropriate
layer. Do not demand a unit test when an existing integration or end-to-end test
more directly covers the contract.

A missing-test comment must name the unverified behavior and a concrete scenario
and assertion that would catch a realistic regression. Do not leave a generic
"add tests" comment or prescribe test-file structure. When deterministic testing
is genuinely impractical, ask for specific reproducible verification evidence
and the reason it cannot be automated.
<!-- configure-ai-review:baseline:end -->

## Repository-specific review guidance

### Toolchain

- oblt-aw is primarily GitHub Actions/gh-aw YAML and Python control-plane scripts, with TypeScript tests; CI tool versions are pinned in `.github/workflows/ci.yml`.

### Focus areas

- When event clients, routes, or `config/<org>/` change, trace the org-scoped event-to-route and allow-list flow; mismatches can silently skip an intended agent or run it for the wrong organization.
- When client workflows change, verify the distributed template under `.github/remote-workflow-template/<org>/` remains the source of truth; editing only an installed copy leaves fleet consumers stale.
- When live E2E gates or fixtures change, verify full producer-to-outcome-to-oracle evidence and fixture identity; a substitute signal can falsely pass a safety check.

### Deterministic checks — skip reported findings

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
- `validate_aw_workflow_permissions.py` checks reusable-workflow caller permissions.
- `make compile-aw-check` checks gh-aw generated lock files against their Markdown sources.
- `npm test` runs the TypeScript unit tests.
- OpenSSF Scorecard reports repository security posture.

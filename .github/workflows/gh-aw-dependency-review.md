---
inlined-imports: true
description: "Analyze Dependabot, Renovate, and Updatecli dependency update PRs"
imports:
  - gh-aw-fragments/ephemeral-github-token.md
  - gh-aw-fragments/elastic-tools.md
  - gh-aw-fragments/runtime-setup.md
  - gh-aw-fragments/formatting.md
  - gh-aw-fragments/rigor.md
  - gh-aw-fragments/mcp-pagination.md
  - gh-aw-fragments/messages-footer.md
  - gh-aw-fragments/safe-output-add-comment-pr.md
  # Hardcoded merge-ready allowlist (not a workflow_call input — callers cannot widen it).
  - gh-aw-fragments/safe-output-add-labels-merge-ready.md
  - gh-aw-fragments/network-ecosystems.md
  - gh-aw-fragments/obs-defaults.md
engine:
  id: copilot
  concurrency:
    group: "gh-aw-copilot-${{ github.workflow }}-dependency-review-${{ github.event.pull_request.number }}"
on:
  stale-check: false
  workflow_call:
    inputs:
      additional-instructions:
        description: "Repo-specific instructions appended to the agent prompt"
        type: string
        required: false
        default: ""
      setup-commands:
        description: "Shell commands to run before the agent starts (dependency install, build, etc.)"
        type: string
        required: false
        default: ""
      github-token-policy:
        description: "Elastic TokenPolicy id for create-token. When set, mint an OIDC ephemeral token so labels/comments re-trigger downstream workflows. Leave empty to use GITHUB_TOKEN."
        type: string
        required: false
        default: ""
    secrets:
      GH_AW_GITHUB_TOKEN:
        required: false
  roles: [admin, maintainer, write]
  # Hardcoded to config/obs/allowed_pr_authors.json (GH-AW cannot declare on.bots in fragments).
  bots:
    - "dependabot[bot]"
    - "renovate[bot]"
    - "Dependabot"
    - "Renovate"
    - "elastic-vault-github-plugin-prod[bot]"
    - "github-actions[bot]"
concurrency:
  group: ${{ github.workflow }}-dependency-review-${{ github.event.pull_request.number }}
  cancel-in-progress: true
# Map workflow_call policy input into the shared ephemeral-token fragment
# (resolves WORKFLOW_TOKEN_POLICY / WORKFLOW_TOKEN_POLICY_CONFIG).
env:
  WORKFLOW_TOKEN_POLICY: ${{ inputs.github-token-policy }}
permissions:
  copilot-requests: write
  actions: read
  contents: read
  issues: read
  pull-requests: read
  id-token: write
tools:
  github:
    # Override obs-defaults trusted-users so bot authors in on.bots are trusted.
    trusted-users: "dependabot[bot],renovate[bot],Dependabot,Renovate,elastic-vault-github-plugin-prod[bot],github-actions[bot]"
    toolsets: [repos, issues, pull_requests, search, actions]
  bash: true
  web-fetch:
safe-outputs:
  activation-comments: false
  # Also listed in obs-defaults; gh-aw v0.88.7 does not merge report-failed-jobs from imports.
  report-failed-jobs: false
strict: false
timeout-minutes: 60
steps:
  # REST injection for Actions commit.verification (issue #2097). Runs on the
  # runner with GITHUB_TOKEN before the agent sandbox; MCP get_commit omits
  # verification fields. Always fetch the collector from an immutable
  # elastic/oblt-aw commit into RUNNER_TEMP (never execute the PR checkout
  # copy). Bump COLLECTOR_REF + COLLECTOR_SHA256 together when the script changes.
  - name: Collect Actions commit verification (REST)
    env:
      GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      GITHUB_REPOSITORY: ${{ github.repository }}
      PR_NUMBER: ${{ github.event.pull_request.number }}
      # Last commit that changed scripts/obs/collect_actions_commit_verification.py
      COLLECTOR_REF: 29d42a0660f6afe9f5c1e687d6570287c29fbad3
      COLLECTOR_SHA256: 718e6e1a70827f6161537ac48518c295abbcacf3ad5295ab7d2e814771005170
    run: |
      set -euo pipefail
      OUT="${GITHUB_WORKSPACE}/actions-commit-verification.json"
      mkdir -p "${RUNNER_TEMP}/oblt-aw-tools"
      SCRIPT="${RUNNER_TEMP}/oblt-aw-tools/collect_actions_commit_verification.py"
      gh api "repos/elastic/oblt-aw/contents/scripts/obs/collect_actions_commit_verification.py?ref=${COLLECTOR_REF}" \
        --jq .content | base64 --decode > "${SCRIPT}"
      actual="$(shasum -a 256 "${SCRIPT}" | awk '{print $1}')"
      if [[ "${actual}" != "${COLLECTOR_SHA256}" ]]; then
        echo "::error::collector integrity check failed (got ${actual}, expected ${COLLECTOR_SHA256})"
        exit 1
      fi
      if [[ -z "${PR_NUMBER}" ]]; then
        echo "::warning::pull_request.number missing; writing empty Actions verification facts"
        printf '%s\n' '{"version":1,"source":"github-rest-commit-verification","pins":[]}' > "${OUT}"
        exit 0
      fi
      python3 "${SCRIPT}" \
        --pull-number "${PR_NUMBER}" \
        --output "${OUT}"
  - name: Repo-specific setup
    if: ${{ inputs.setup-commands != '' }}
    env:
      SETUP_COMMANDS: ${{ inputs.setup-commands }}
      GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    run: eval "$SETUP_COMMANDS"
---

# Dependency Review Agent

Analyze dependency update pull requests (Dependabot, Renovate, Updatecli) in ${{ github.repository }}. Provide a detailed analysis comment covering changelog highlights, compatibility, risk, and ecosystem-specific checks.

## Context

- **Repository**: ${{ github.repository }}
- **PR**: #${{ github.event.pull_request.number }} — ${{ github.event.pull_request.title }}
- **PR Author**: ${{ github.actor }}

## Constraints

This workflow is read-only. You can read files, search code, run commands, and comment on PRs — but your only outputs are an analysis comment and optional labels.

### GitHub reads and safe outputs (mandatory)

- The pull request head is already checked out in `GITHUB_WORKSPACE`. Start by reading the local PR diff (e.g. `git --no-pager log --name-status --oneline -n 50` to see changed files, and `git --no-pager diff --name-only HEAD~1..HEAD` for single-commit PRs) to identify dependency updates. Do **not** stop solely because shell `gh` cannot reach GitHub.
- Shell `gh` is **not** authenticated in the agent sandbox. That does **not** mean GitHub is unreachable.
- When you need GitHub API data (PR metadata, release notes), use the read-only **GitHub MCP**. Do not use shell `gh` for those reads.
- **Actions commit verification:** Do **not** use MCP `get_commit` (or shell `gh`) for `commit.verification`. A pre-agent runner step writes `actions-commit-verification.json` at the workspace root using GitHub REST. That file is the **only** source of truth for the Actions commit-verification ecosystem check.
- Before finishing you **MUST** call at least one safe-output tool: `add_comment`, `add_labels`, `noop`, `report_incomplete`, `missing_tool`, or `missing_data`. A text-only exit with zero safe outputs is a failure.
- Use `noop` only when the PR truly has no dependency updates to review. If you cannot gather enough context to analyze a real dependency update, call `report_incomplete` (or `missing_tool` / `missing_data`) — do not claim noop in prose and do not exit without a tool call.

### Noop when not applicable (mandatory)

- If the PR has NO dependency updates to review (no version, pin, digest, or lockfile bumps in changed files), you MUST call `noop` — do NOT call `add_comment` (no analysis comment from the agent).
- Use the format: {"noop": {"message": "No action needed: [brief explanation]"}}
- Example: "No action needed: no dependency version updates found in the PR diff"
- Do **not** noop a PR that clearly bumps a version/pin/digest/lockfile solely because the bump type is unfamiliar or is not Actions/Go/npm. Analyze it (ecosystem **other** is fine) and apply Step 4.
- Do not emit an analysis comment for no-op outcomes. The noop tool provides transparency; a separate control-plane job may still note an empty `comment_id` on the PR.

## Instructions

### Step 1: Gather Context

1. Prefer the local checkout first (see GitHub reads above). Use GitHub MCP `pull_request_read` when you need PR metadata, full diff, or file list beyond what the local checkout shows.
2. Identify changed files and whether they indicate dependency version updates.

### Step 2: Identify and Classify Updated Dependencies

Parse the diff to identify each dependency being updated. For each dependency, extract:
- **Ecosystem**: a short label for the bump kind (see path families below), or **other** when unclear
- **Package name**: identifier being bumped (action, module, package, image/env pin name, etc.)
- **Old version**: tag, SHA, digest, or pin before the update
- **New version**: tag, SHA, digest, or pin after the update

Classify by **changed paths** and **what the diff bumps**. Prefer these path families (aligned with `config/obs/automerge-dependency-collections.json` globs — do **not** invent ecosystems that are not represented there):

- `.github/workflows/**`, `.github/actions/**`, `**/action.yml`, `**/action.yaml` → **GitHub Actions**
- `.pre-commit-config.yaml` → **pre-commit**
- `go.mod`, `go.sum`, `**/go.mod`, `**/go.sum` (and related NOTICE / `beats` bumps when those land together) → **Go** (or Go + related manifests)
- `package.json`, `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml` (and `**/` variants) → **npm/Node**
- `pyproject.toml`, `requirements*.txt`, `Pipfile*`, `poetry.lock`, `uv.lock` (and `**/` variants) → **Python**
- `**/*.tf`, `**/*.tfvars`, `**/.terraform.lock.hcl`, `**/terragrunt.hcl`, version pin files for Terraform/OpenTofu/Terragrunt → **Terraform**
- `**/*.rego`, `**/.opa-version`, `**/opa.yaml`, `**/opa.yml` → **Open Policy Agent**
- `.package-version`, `**/.package-version` → **package-version**
- `.buildkite/**`, `**/Dockerfile`, `**/Dockerfile.*`, `**/docker-compose.yml`, `**/docker-compose.yaml`, `testing/environments/snapshot.yml` → **CI / container / snapshot image pins** when the diff bumps runner, container, or snapshot **image** identifiers or env pins. There is **no** separate “Buildkite plugin” dependency collection: do **not** map every `.buildkite/**` change to “Buildkite plugin.” If a `.buildkite/` diff bumps a plugin SHA/tag instead of an image pin, still treat it as an in-scope version bump; label the ecosystem **other** (or note “Buildkite plugin pin” as the bump type in the analysis) and continue — do **not** noop.
- `pom.xml`, `build.gradle`, `build.gradle.kts`, `gradle.lockfile` → **Java/Kotlin (Maven/Gradle)**
- Other version/pin/lockfile bumps → **other** (still in-scope; analyze them)

Any clear version, pin, digest, or lockfile bump in the families above is a dependency update to review.

### Step 3: Analyze Each Dependency

For each updated dependency, perform the following checks:

#### 3a: Commit Verification (GitHub Actions only)

If the action reference uses a commit SHA (e.g. `uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd`):

1. Read **`actions-commit-verification.json`** at the workspace root (pre-agent REST facts). Match each SHA-pinned Action in the PR by `action` + `sha` (or by `sha` alone when unique).
2. Apply this decision table (mandatory):
   - **`verified: true`** → Commit verified ✅. Ecosystem commit check **passes** for this pin.
   - **`verified: false`** → Commit verified ⚠️ No (`reason` when present). Ecosystem commit check **fails** for this pin. Unverified / unsigned Action pins are a supply-chain risk — do **not** apply `oblt-aw/ai/merge-ready`.
   - **`verified` is null / pin missing / `error` set** → verification data is **unavailable**. Call `missing_data` or `report_incomplete` explaining the gap. Do **not** invent “MCP field not exposed”, do **not** mark overall risk **moderate** solely because verification data is missing, and do **not** post a full low-risk analysis that withholds the label only for that reason.
3. Do **not** call MCP `get_commit` (or shell `gh`) to re-check `commit.verification` — MCP responses omit those fields and caused false negatives.
4. Still check whether the commit SHA corresponds to a known release tag and that the tag points at the expected SHA (MCP releases/tags is fine for tag mapping). Tag mapping does **not** replace a `verified: false` result from the facts file.

#### 3b: Changelog and Release Notes

For dependencies hosted on GitHub, fetch the release notes via GitHub MCP / API:
1. Fetch the release notes for the new version from the dependency's repository.
2. If no release exists for the exact tag, check the latest releases.
3. For non-GitHub dependencies, check the package registry or changelog files in the source repo when available.
4. Summarize key changes between the old and new versions, focusing on:
   - Breaking changes or removed features
   - New required configuration or changed defaults
   - Security fixes
   - Deprecations
   - Notable new features relevant to how this repo uses the dependency

Expand the analysis with a **CVE-focused assessment** based on changelog and release-note content for each updated dependency.

Required additions for each dependency:
- Identify vulnerability-related entries (CVE IDs, GHSA advisories, security fixes, patched classes/functions/modules).
- Analyze internal implementation changes in the new version that can affect vulnerability exposure (authn/authz logic, crypto/TLS handling, deserialization/parsing, input validation/sanitization, dependency graph updates, default security settings, sandboxing/isolation, permission scopes).
- Explain whether the internal changes reduce, preserve, or increase risk for this repository usage.
- Explicitly call out any potential regressions or newly introduced attack surface.

#### 3c: Usage Analysis

1. Search the repository for all places the dependency is used. The search method depends on the ecosystem:
   - **GitHub Actions**: `grep -rn '{owner}/{repo}' .github/workflows/ --include='*.yml' --include='*.yaml'`
   - **Go**: `grep -rn '{module}' --include='*.go'` (look for import statements)
   - **npm/Node**: `grep -rn "require('{package}')\|from '{package}'" --include='*.js' --include='*.ts' --include='*.mjs' --include='*.cjs'`
   - **Python**: `grep -rn "import {package}\|from {package}" --include='*.py'`
   - **Java**: `grep -rn '{groupId}' --include='*.java' --include='*.kt' --include='*.gradle' --include='*.xml'`
2. For each usage, note:
   - Which files and modules use it
   - What APIs, functions, or features are consumed
   - For GitHub Actions: what inputs are passed and outputs consumed
   - For GitHub Actions: what events trigger the workflow

3. Cross-reference the usage against the changelog:
   - Are any APIs, inputs, or features used by this repo deprecated or removed in the new version?
   - Are there breaking changes to consumed interfaces?
   - Are there new required configuration options that are not provided?

#### 3d: Testability Assessment

1. Check the trigger events for each workflow that uses the updated dependency.
2. If a workflow is **only** triggered by `push` (to main/default branch), `release`, `schedule`, or `workflow_dispatch`, it **cannot be validated by the PR itself**. Flag this as higher risk.
3. If a workflow is triggered by `pull_request` or `pull_request_target`, it can be exercised in the PR context.

#### 3e: Pin Format Check (plugin / action SHA-or-tag pins)

When the bump is a **plugin or Action** pin that uses a SHA or mutable tag (not an image/env pin):
1. Check if the update moves from a SHA-pinned version to a mutable tag (higher risk).
2. Check if the update moves from one mutable tag to another mutable tag (moderate risk).
3. SHA-to-SHA or tag-to-SHA-pinned updates are preferred.

Skip this section for pure CI/container/snapshot **image** identifier or env pin bumps.

#### 3f: Ecosystem-Specific Guidance

Apply the following additional checks based on the dependency ecosystem:

**Go modules:**
- Check if this is a major version bump (e.g. v1 → v2) — Go major versions change the import path, which is a breaking change requiring code updates across the repo.
- For indirect dependency updates, note that these are transitive and generally lower risk.
- Check for `// Deprecated:` annotations in the module if accessible.

**npm / Node packages:**
- Check if this is a major semver bump — major versions typically signal breaking changes.
- Look for peer dependency conflicts that may arise from the update.
- For `devDependencies`, note that these only affect development and CI, not production.

**Python packages (pip, Poetry, uv):**
- Check if this is a major version bump — may indicate breaking API changes.
- Check for minimum Python version requirements that may have changed.
- For packages with native extensions (e.g. `numpy`, `cryptography`), note potential build or platform compatibility changes.

**Java / Kotlin (Maven, Gradle):**
- Check if this is a major version bump — may indicate breaking API changes.
- Note if the groupId or artifactId changed (dependency relocation).
- For Spring or framework dependencies, check for minimum JDK version changes.

### Step 4: Determine Labels (`oblt-aw/ai/merge-ready`)

The only classification label this Observability-owned workflow may apply is **`oblt-aw/ai/merge-ready`**.

First assign an overall risk level for the PR: **low**, **low-to-moderate**, **moderate**, or **high**, using the CVE-focused analysis above (scope of vulnerable surface in this repo, quality of the fix, blast radius, and whether behavior changes are contained).

Apply `oblt-aw/ai/merge-ready` when ALL of the following are true:
- Overall risk is **low** OR **low-to-moderate** (including when changelogs mention CVEs, GHSAs, or security fixes—those entries do **not** disqualify the label in these two bands; they must still be documented in your analysis).
- No breaking changes to APIs, inputs, or features used by this repository.
- Ecosystem checks pass (Actions commit verification per Step 3a / `actions-commit-verification.json`, pin format acceptable when Step 3e applies, etc.).
- Workflows using the dependency are testable in PR context (pull_request or pull_request_target trigger), OR the dependency is dev-only / CI-only (e.g. pre-commit, linters, CI image pins) with no production application impact.

Minor behavioral changes (e.g. ignore-pattern handling, formatting) that do not affect this repo's usage do NOT disqualify the label when risk is low or low-to-moderate.

Do NOT add `oblt-aw/ai/merge-ready` when: overall risk is **moderate** or **high**, breaking changes affect this repo, ecosystem checks fail (including any Actions pin with `verified: false` in the facts file), or workflows are untestable and the dependency has production impact.

Missing Actions verification data (`verified: null` / missing pin / collector error) is **not** an automatic moderate-risk or soft “withhold label while claiming low risk” outcome — use `missing_data` / `report_incomplete` per Step 3a.

### Step 5: Post Analysis Comment

Call `add_comment` on the PR with a structured analysis. Use the following format:

> ## Dependency Update Analysis
>
> **Summary**: [One-line summary of the update and overall risk assessment]
>
> ### [Dependency 1: package vOLD → vNEW]
>
> **Ecosystem**: [GitHub Actions / Go / npm / Python / Java / Terraform / OPA / pre-commit / CI image pin / other]
>
> | Check | Result |
> | --- | --- |
> | Breaking changes | ✅ None found / ⚠️ Found (details below) |
> | Testable in PR | ✅ Yes / ⚠️ No — workflow only runs on [events] |
> | Commit verified | ✅ Yes / ⚠️ No / ⚠️ Unavailable *(GitHub Actions only; from `actions-commit-verification.json`)* |
> | Pin format | ✅ SHA-pinned / ⚠️ Mutable tag *(GitHub Actions / plugin SHA-or-tag pins only)* |
>
> Only include rows relevant to the dependency ecosystem. For example, "Commit verified" and "Pin format" only apply when Step 3a / 3e apply.
>
> <details>
> <summary>Changelog highlights (vOLD → vNEW)</summary>
>
> [Key changes from release notes]
> </details>
>
> <details>
> <summary>Usage in this repository</summary>
>
> [List of files/modules using this dependency and relevant APIs/inputs/outputs]
> </details>
>
> <details>
> <summary>Compatibility assessment</summary>
>
> [Analysis of whether current usage is compatible with the new version, including ecosystem-specific notes]
> </details>
>
> ### Labels Applied
> [List of labels applied and why, or "No labels applied"]

If the analysis found no issues, keep the comment concise — do not pad with unnecessary detail.

### Step 6: Apply Labels

Label application (mandatory):
- When ALL criteria for `oblt-aw/ai/merge-ready` are met, you MUST call `add_labels` with that label. Do not only recommend it in the comment; apply it via the add_labels tool.
- The comment's "Labels Applied" section must reflect labels you actually applied via add_labels, not merely recommended. If you applied a label, say so; if you did not apply any, say "No labels applied."

${{ inputs.additional-instructions }}

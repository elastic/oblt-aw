# Security Scanning Ruleset

## Overview

This document defines the ruleset used by the oblt-aw security detector to identify vulnerabilities in GitHub Actions workflows, shell scripts, and related artifacts. It supports the detector–triage–fixer flow in [docs/architecture/security-agent-architecture.md](../architecture/security-agent-architecture.md).

**Scope**: Workflow YAML (`.github/workflows/**`), shell scripts, dependency manifests when present, and patterns aligned with [elastic/observability-robots#3758](https://github.com/elastic/observability-robots/issues/3758).

**Detector:** Implements every SEC-0xx rule defined in this document (currently **SEC-001–SEC-003**, **SEC-010–SEC-012**, **SEC-020–SEC-022**, **SEC-030–SEC-035**, and **SEC-040–SEC-044**), except where a rule explicitly defers to another workflow (for example dependency review at PR time). See **Implementation notes** at the end of this document. [oblt-actions#500](https://github.com/elastic/oblt-actions/issues/500) illustrates token exposure patterns covered by SEC-001–SEC-003.

---

## Traceability: Issue #3758 Security Focus Areas

[Issue #3758](https://github.com/elastic/observability-robots/issues/3758) defines four focus areas. Every rule below maps to at least one area so the full proposal is covered.

| Focus area (issue) | Sub-topics from issue | Rule IDs | Primary detection approach |
|--------------------|----------------------|----------|----------------------------|
| **1. Injection vulnerabilities** | Expression injection in workflows; command injection in shell; YAML injection | SEC-010–SEC-012 | Semgrep / pattern scans on YAML; shellcheck + shell patterns on scripts |
| **2. Secret management** | Token exposure via CLI args; secrets in logs or artifacts; improper token scoping | SEC-001–SEC-003, SEC-020–SEC-022 | Pattern scans on workflows and scripts; optional secret scanners for literals |
| **3. Supply chain security** | Binary integrity; dependency pinning and verification; third-party action auditing | SEC-030–SEC-032, SEC-033–SEC-035 | Workflow `uses:` parsing; script patterns for downloads; lockfile + audit CLIs |
| **4. Least privilege** | Minimal token permissions; proper `GITHUB_TOKEN` scoping; resource access restrictions | SEC-040–SEC-044 | YAML analysis of `permissions:`; job-level vs workflow-level; dangerous token patterns |

**Phase 1 scanning list from the issue** maps as follows:

| Issue Phase 1 item | How it is covered |
|--------------------|-------------------|
| GitHub Actions security best practices checks | SEC-040–SEC-044, SEC-030, and workflow-structure rules |
| Secret scanning patterns | SEC-001–SEC-003, SEC-020–SEC-022 |
| Shell script security analysis (shellcheck with security relevance) | SEC-011 and shellcheck-backed findings (quoting, unsafe eval) |
| Dependency vulnerability scanning | SEC-033–SEC-035 (manifests in repo); complementary: `gh-aw-dependency-review` via ingress for rich GitHub Dependency Review |
| YAML injection pattern detection | SEC-010, SEC-012 |

**Complementary workflow (not a duplicate ruleset):** Repositories using oblt-aw ingress may already run [`gh-aw-dependency-review`](./gh-aw-dependency-review.md) for **dependency and license** signals at PR time. The **security detector** still implements SEC-033–SEC-035 where lockfiles or manifests exist without a PR, and aligns severity/titles with this ruleset.

---

## Severity Levels

| Level | Label | Description |
|-------|-------|-------------|
| **Critical** | `oblt-aw/severity/critical` | Direct credential exposure, hardcoded secrets, or equivalent. |
| **High** | `oblt-aw/severity/high` | Exploitable misconfiguration (injection, missing integrity check on binaries, secrets in logs). |
| **Medium** | `oblt-aw/severity/medium` | Supply-chain or privilege issues with lower immediate exploitability. |
| **Low** | `oblt-aw/severity/low` | Best-practice gaps and defense-in-depth. |

---

## 1. Secret Management (token exposure, logs, scoping)

### Rule SEC-001: Token or Secret in `run:` Arguments

**Severity**: Critical
**Maps to**: Secret management — token exposure via command-line arguments; Phase 1 secret scanning patterns.

**Description**: Secrets or tokens must not be passed as command-line arguments. Process arguments are visible in process listings (e.g., `ps`, `/proc`) and in logs.

**Pattern**: Any `run:` block where `${{ secrets.* }}` (or secret-bearing `env`) is interpolated into the command string in a way that passes the secret as an argv token.

**Example (violation)**:

```yaml
- run: gh api /repos/${{ github.repository }} --header "Authorization: Bearer ${{ secrets.GITHUB_TOKEN }}"
```

**Example (compliant)**:

```yaml
- env:
    GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  run: gh api /repos/${{ github.repository }}
```

---

### Rule SEC-002: `${{ secrets.* }}` in Command Strings

**Severity**: High
**Maps to**: Secret management — secrets in logs or artifacts (indirect: interpolation often logs); Phase 1 secret scanning patterns.

**Description**: `${{ secrets.* }}` must not appear inside `run:` command strings. Use `env:` and environment variables.

**Pattern**: `run:` block containing `${{ secrets.` in the command text.

---

### Rule SEC-003: Env Indirection Requirement

**Severity**: High
**Maps to**: Secret management — same as SEC-001/002; aligns with [oblt-actions#495](https://github.com/elastic/oblt-actions/issues/495) (env injection hardening).

**Description**: Secrets must be passed via `env:` and referenced as environment variables in scripts, not interpolated into workflow command strings.

---

### Rule SEC-020: Hardcoded Secret Pattern

**Severity**: Critical
**Maps to**: Secret management; Phase 1 secret scanning patterns.

**Description**: Literal high-entropy tokens, API keys, or private keys in workflow YAML, shell scripts, or repo config (excluding documented placeholders).

**Detection**: Regex/heuristic scanners (e.g. generic secret patterns); optional integration with GitHub secret scanning parity rules where feasible offline.

---

### Rule SEC-021: Secret or Token Likely Logged

**Severity**: High
**Maps to**: Secret management — secrets in logs or artifacts.

**Description**: Workflows or scripts that print environment variables containing secret names, use `set -x` in steps that handle secrets, `echo` of `*TOKEN*`, `*SECRET*`, or pipe secret env to `tee`/`cat`.

**Pattern examples**: `echo $GITHUB_TOKEN`, `printenv`, `env |`, `set -x` immediately before commands using secrets without `set +x`.

---

### Rule SEC-022: Improper Secret / Token Scoping in Workflow

**Severity**: Medium
**Maps to**: Secret management — improper token scoping (workflow design).

**Description**: A job or step has access to repository secrets or `GITHUB_TOKEN` write scopes when the job only needs read-only operations; or secrets declared at workflow level when only one job requires them (broader blast radius).

**Note**: Overlaps with SEC-041; SEC-022 emphasizes **secret** exposure surface, SEC-041 emphasizes **permissions** syntax.

---

## 2. Injection Vulnerabilities

### Rule SEC-010: Expression Injection Risk in Workflows

**Severity**: High
**Maps to**: Injection — expression injection in workflows; Phase 1 YAML injection pattern detection.

**Description**: Untrusted or attacker-influenced data from `github.event.*` (e.g. issue title/body, PR title, comment body) is interpolated into `run:` commands or into fields that affect command execution without sanitization.

**Pattern**: `${{ github.event.issue.title }}`, `github.event.comment.body`, `github.event.pull_request.title` embedded directly in shell strings used with `run:`.

**Remediation guidance**: Pass values through environment variables with strict quoting, use intermediate scripts with validation, or restrict to trusted event types.

---

### Rule SEC-011: Command Injection in Shell Scripts

**Severity**: High
**Maps to**: Injection — command injection in shell scripts; shellcheck-backed analysis.

**Description**: Unquoted variables, `eval` on variables, or dynamic `$(curl …)` used with user-influenced input in scripts invoked from workflows.

**Detection**: **shellcheck** (e.g. SC2086, SC2119); additional patterns for `eval`, `source` of untrusted paths.

---

### Rule SEC-012: YAML / Workflow Structure Injection

**Severity**: Medium
**Maps to**: Injection — YAML injection attacks; Phase 1 YAML injection pattern detection.

**Description**: User-controlled inputs used to populate `matrix`, `strategy`, dynamic `uses:`, or file paths that select which workflow fragment runs, enabling unexpected code paths.

**Pattern**: `github.event.inputs.*` or `inputs.*` directly concatenated into `uses:`, cache keys that include unsanitized input, or matrix axes built from untrusted strings without allowlists.

---

## 3. Supply Chain Security

### Rule SEC-030: Action Reference Not Pinning to Immutable Revision

**Severity**: Medium
**Maps to**: Supply chain — dependency pinning and verification; third-party action auditing.

**Description**: Third-party actions (`uses:`) should pin to a full commit SHA per [GitHub hardening guidance](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions#using-third-party-actions). Tag-only or branch refs are higher drift and takeover risk.

**Pattern**: `uses: org/name@main`, `uses: org/name@v1` without SHA (policy may allow `actions/*` exceptions if documented).

---

### Rule SEC-031: Third-Party or High-Risk Action Source

**Severity**: Medium
**Maps to**: Supply chain — third-party action auditing.

**Description**: Actions from namespaces outside `actions/` and `github/` (or an org allowlist) require explicit review; detector flags for visibility.

**Note**: Severity may be informational in internal repos with approved third parties; triage can apply `oblt-aw/triage/other` when accepted risk is documented.

---

### Rule SEC-032: Binary or Artifact Download Without Integrity Verification

**Severity**: High
**Maps to**: Supply chain — binary integrity (checksums, signatures); [oblt-actions#496](https://github.com/elastic/oblt-actions/issues/496), [#497](https://github.com/elastic/oblt-actions/issues/497).

**Description**: Scripts download executables or archives with `curl`, `wget`, or `Invoke-WebRequest` without a subsequent cryptographic verification step (checksum compare, `shasum -c`, minisign, cosign as applicable).

**Pattern**: HTTP fetch of binaries without paired `sha256sum`/GPG verify in the same script path.

---

### Rule SEC-033: Dependency Vulnerabilities (Manifests and Lockfiles)

**Severity**: High (depends on CVE)
**Maps to**: Supply chain — dependency pinning and verification; Phase 1 dependency vulnerability scanning.

**Description**: Known-vulnerable dependencies declared in lockfiles or manifests in the repository (e.g. `package-lock.json` + `npm audit`, `Pipfile.lock` / `requirements*.txt` + `pip-audit`, Go modules + `govulncheck` when available).

**Detection**: Run ecosystem-appropriate audit commands in the detector when corresponding files exist; emit one issue per tool run or aggregate per CVE with caps to avoid spam.

---

### Rule SEC-034: Unpinned or Floating Dependency Specifiers

**Severity**: Medium
**Maps to**: Supply chain — dependency pinning and verification.

**Description**: Manifests use unconstrained versions (`*`, `latest`, missing lockfile where ecosystem expects one) increasing supply-chain risk.

---

### Rule SEC-035: Script Invokes Package Install Without Integrity Flags

**Severity**: Low
**Maps to**: Supply chain.

**Description**: `pip install` without hashes, `npm install` without lockfile enforcement in CI scripts where `npm ci` is expected.

---

## 4. Least Privilege

### Rule SEC-040: Overly Broad `permissions`

**Severity**: Medium
**Maps to**: Least privilege — minimal token permissions.

**Description**: Workflow or job sets `permissions: write-all`, `contents: write` for all jobs when read suffices, or grants `id-token`, `packages`, `security-events` without need.

---

### Rule SEC-041: `GITHUB_TOKEN` or PAT Scope Broader Than Necessary

**Severity**: Medium
**Maps to**: Least privilege — proper `GITHUB_TOKEN` scoping.

**Description**: Jobs that only comment or read metadata use tokens with `contents: write`, `metadata: write` bundles, or custom PATs with org-wide scopes.

---

### Rule SEC-042: Elevated or Dangerous Execution Context

**Severity**: Low
**Maps to**: Least privilege — resource access restrictions.

**Description**: Use of `sudo`, container `options: --privileged`, or running as root in custom images where unprivileged execution is possible.

---

### Rule SEC-043: Sensitive Workflow on High-Risk Triggers

**Severity**: Medium
**Maps to**: Least privilege — resource access restrictions; injection overlap.

**Description**: Workflows that run untrusted code or check out PR head with write-capable `GITHUB_TOKEN` on `pull_request_target`, or combine secrets with fork PRs against [GitHub recommendations](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions#preventing-pwn-requests).

**Pattern**: `pull_request_target` with checkout of PR head and secret-using steps without explicit guard patterns.

---

### Rule SEC-044: Missing Explicit `permissions` (Default Too Permissive for Fork PRs)

**Severity**: Low
**Maps to**: Least privilege.

**Description**: Workflow omits top-level `permissions:` where repository default grants broader access than the job requires; recommend explicit least-privilege block.

---

## Implementation Notes

- **Implementation:** Map each rule ID to a check in the detector scripts or job matrix. Complementary ingress workflows (for example `gh-aw-dependency-review`) may supplement dependency findings where SEC-033–SEC-035 reference PR-time review.
- **False positives**: Expression-injection rules (SEC-010) may need triage tuning; during early rollout, triage may temporarily down-rank individual findings to Medium until confidence improves, while SEC-010 remains defined as High severity.
- **Dependency overlap**: For PR-time dependency review, prefer enabling `gh-aw-dependency-review` in ingress; SEC-033 remains for scheduled full-repo audits without a PR.

---

## References

- [GitHub Actions security hardening](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)
- [elastic/observability-robots#3758](https://github.com/elastic/observability-robots/issues/3758) — focus areas and phases
- [elastic/oblt-actions#500](https://github.com/elastic/oblt-actions/issues/500) — token exposure via CLI args
- [elastic/oblt-actions#495](https://github.com/elastic/oblt-actions/issues/495) — GH_TOKEN handling
- [elastic/oblt-actions#496](https://github.com/elastic/oblt-actions/issues/496), [#497](https://github.com/elastic/oblt-actions/issues/497) — binary integrity

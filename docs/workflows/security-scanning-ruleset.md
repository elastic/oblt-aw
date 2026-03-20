# Security Scanning Ruleset

## Overview

This document defines the ruleset used by the oblt-aw security detector to identify vulnerabilities in GitHub Actions workflows and shell scripts. The ruleset supports the detector–triage–fixer flow described in `docs/architecture/security-agent-architecture.md`.

**Scope**: GitHub Actions YAML, shell scripts invoked by workflows, and related configuration.

**Initial ruleset focus**: Token and secret exposure via command-line arguments (see [oblt-actions#500](https://github.com/elastic/oblt-actions/issues/500)).

---

## Severity Levels

| Level | Label | Description |
|-------|-------|-------------|
| **Critical** | `oblt-aw/severity/critical` | Direct secret exposure; high likelihood of credential leakage (e.g., secrets in process args visible to other processes). |
| **High** | `oblt-aw/severity/high` | Secret or token used in an unsafe context (e.g., `${{ secrets.* }}` in command strings); requires immediate remediation. |
| **Medium** | `oblt-aw/severity/medium` | Potential exposure or misconfiguration; lower exploitability but still actionable. |
| **Low** | `oblt-aw/severity/low` | Best-practice violation; hardening opportunity. |

### Classification Criteria

- **Critical**: Secret or token passed as a command-line argument to any executable; secret interpolated into a shell command string.
- **High**: `${{ secrets.* }}` or `${{ env.* }}` containing secrets used in `run:` inline command strings; env indirection not used where required.
- **Medium**: Patterns that could lead to exposure under certain conditions; deprecated or weak secret handling.
- **Low**: Missing least-privilege permissions; non-secret but security-relevant misconfigurations.

---

## Rules: Token and Secret Exposure

The security detector implements the following rules for this category.

### Rule SEC-001: Token or Secret in `run:` Arguments

**Severity**: Critical

**Description**: Secrets or tokens must not be passed as command-line arguments. Process arguments are visible in process listings (e.g., `ps`, `/proc`) and in logs.

**Pattern**: Any `run:` block where a `${{ secrets.* }}` or `${{ env.* }}` (when env contains secrets) is interpolated into the command string.

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

**Description**: GitHub Actions expressions `${{ secrets.* }}` must not appear inside `run:` command strings. Use `env:` to pass secrets as environment variables instead.

**Pattern**: `run:` block containing `${{ secrets.` in the command text.

**Example (violation)**:

```yaml
- run: |
    echo "Deploying with token ${{ secrets.DEPLOY_TOKEN }}"
    curl -H "Authorization: Bearer ${{ secrets.DEPLOY_TOKEN }}" ...
```

**Example (compliant)**:

```yaml
- env:
    DEPLOY_TOKEN: ${{ secrets.DEPLOY_TOKEN }}
  run: |
    echo "Deploying with token"
    curl -H "Authorization: Bearer $DEPLOY_TOKEN" ...
```

---

### Rule SEC-003: Env Indirection Requirement

**Severity**: High

**Description**: When a secret is needed in a script or command, it must be passed via `env:` and referenced as an environment variable (e.g., `$VAR`), not interpolated into the command string.

**Pattern**: Script or command that uses a secret; check that the secret is defined in `env:` and the command uses `$VAR` (or equivalent) rather than `${{ secrets.* }}`.

**Example (violation)**:

```yaml
- run: ./deploy.sh --token=${{ secrets.API_TOKEN }}
```

**Example (compliant)**:

```yaml
- env:
    API_TOKEN: ${{ secrets.API_TOKEN }}
  run: ./deploy.sh --token="$API_TOKEN"
```

**Note**: Passing via `env` and then using `$API_TOKEN` in the command still exposes the value in the process environment. The preferred pattern is to pass the secret via `env:` and have the script read it from the environment (e.g., `export API_TOKEN` before calling a subprocess that needs it), avoiding inclusion in the `run:` string at all when possible. For scripts that must pass tokens to tools, env indirection reduces exposure compared to direct interpolation in the workflow YAML.

---

## Placeholder Rules (Future Expansion)

The following rule categories are reserved for future implementation. Definitions are provisional.

### Injection (Expression, Command, YAML)

| Rule ID | Title | Severity | Description |
|---------|-------|----------|-------------|
| SEC-010 | Expression injection | High | User-controlled or untrusted input interpolated into `${{ }}` expressions. |
| SEC-011 | Command injection | High | Unescaped user input used in shell commands. |
| SEC-012 | YAML injection | Medium | Untrusted input used in YAML structure (e.g., matrix, strategy). |

### Secret Management

| Rule ID | Title | Severity | Description |
|---------|-------|----------|-------------|
| SEC-020 | Hardcoded secret pattern | Critical | Literal tokens, API keys, or passwords in source. |
| SEC-021 | Secret in log output | High | Secret or token likely to appear in job logs. |
| SEC-022 | Overly broad secret scope | Medium | Secret passed to steps that do not need it. |

### Supply Chain

| Rule ID | Title | Severity | Description |
|---------|-------|----------|-------------|
| SEC-030 | Unpinned action reference | Medium | Action used without `@sha256:` or `@<commit>`. |
| SEC-031 | Third-party action risk | Medium | Action from untrusted or unverified source. |
| SEC-032 | Binary integrity | High | Downloaded binaries without checksum verification. |

### Least Privilege

| Rule ID | Title | Severity | Description |
|---------|-------|----------|-------------|
| SEC-040 | Excessive permissions | Medium | Job or workflow uses `permissions: write-all` or broader than needed. |
| SEC-041 | Token scope too broad | Medium | `GITHUB_TOKEN` or custom token has permissions beyond required scope. |
| SEC-042 | Unnecessary `run-as` elevation | Low | Step runs with elevated privileges when not required. |

---

## References

- [GitHub Actions security hardening](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)
- [elastic/oblt-actions#500](https://github.com/elastic/oblt-actions/issues/500) — token exposure via CLI args
- [elastic/oblt-actions#495](https://github.com/elastic/oblt-actions/issues/495) — GH_TOKEN env injection
- [elastic/oblt-actions#496](https://github.com/elastic/oblt-actions/issues/496), [#497](https://github.com/elastic/oblt-actions/issues/497) — binary integrity
- Implementation plan: [elastic/observability-robots#3758](https://github.com/elastic/observability-robots/issues/3758)

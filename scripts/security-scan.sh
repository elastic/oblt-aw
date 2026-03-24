#!/usr/bin/env bash
# Copyright 2026-2027 Elasticsearch B.V.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

# Security scan for oblt-aw detector.
# Aligned with docs/workflows/security-scanning-ruleset.md (SEC-001–SEC-044).
# Output format: file|line|rule|severity|message
set -euo pipefail

REPO_ROOT="${1:-.}"
cd "$REPO_ROOT"

if ! command -v jq >/dev/null 2>&1; then
  echo "security-scan.sh: jq is required" >&2
  exit 1
fi

emit() {
  # file|line|rule|severity|message
  echo "$1|$2|$3|$4|$5"
}

# --- SEC-011: shell scripts (shellcheck; also supports injection heuristics) ---
find . -path './.git' -prune -o -path './node_modules' -prune -o -path './vendor' -prune -o \
  -type f \( -name '*.sh' -o -name '*.bash' \) -print 2>/dev/null | while IFS= read -r f; do
  [ -f "$f" ] || continue
  shellcheck -f json1 "$f" 2>/dev/null | jq -r --arg file "$f" '
    .comments[]? |
    (if .level == "error" then "high"
     elif .level == "warning" then "medium"
     elif .level == "info" then "low"
     else "low" end) as $sev |
    "\($file)|\(.line // 1)|SEC-011|\($sev)|shellcheck [\(.level)]: \(.message)"
  ' 2>/dev/null || true
done

# --- SEC-002 / SEC-001: secrets in workflow YAML (${{ secrets. }}) ---
if [ -d .github/workflows ]; then
  # shellcheck disable=SC2016
  find .github/workflows -type f \( -name '*.yml' -o -name '*.yaml' \) 2>/dev/null | while IFS= read -r wf; do
    awk '
      BEGIN {
        in_run = 0;
        run_indent = -1;
      }
      {
        line = $0;
        # Determine indentation (number of leading spaces).
        indent = match($0, /[^ ]/) - 1;
        if (indent < 0) {
          indent = 0;
        }
        trimmed = $0;
        sub(/^[[:space:]]+/, "", trimmed);

        # Detect start of a run: block (e.g., "run: |", "run: >" or "run: <cmd>").
        if (trimmed ~ /^run:[[:space:]]*($|[|>])/ ) {
          in_run = 1;
          run_indent = indent;
        } else if (in_run) {
          # Heuristic end of run block: a non-empty, non-comment line
          # with indentation <= run_indent.
          if (trimmed !~ /^($|#)/ && indent <= run_indent) {
            in_run = 0;
          }
        }

        if (in_run && line ~ /\${{[[:space:]]*secrets\./) {
          printf "%s:%d:%s\n", FILENAME, FNR, line;
        }
      }
    ' "$wf"
  done | while IFS= read -r line; do
    file=$(echo "$line" | cut -d: -f1)
    line_num=$(echo "$line" | cut -d: -f2)
    snippet=$(echo "$line" | cut -d: -f3- | head -c 200 | tr '|' ' ')
    emit "$file" "$line_num" "SEC-002" "high" "Secret expression in workflow run: block; ensure env: indirection, not argv/logs. Snippet: ${snippet}"
  done || true
fi

# --- SEC-010: expression injection risk (untrusted github.event data in workflows) ---
if [ -d .github/workflows ]; then
  grep -rn --include='*.yml' --include='*.yaml' 'github\.event\.' .github/workflows 2>/dev/null | while IFS= read -r line; do
    file=$(echo "$line" | cut -d: -f1)
    line_num=$(echo "$line" | cut -d: -f2)
    snippet=$(echo "$line" | cut -d: -f3- | head -c 200 | tr '|' ' ')
    emit "$file" "$line_num" "SEC-010" "medium" "github.event data in workflow; validate quoting and trust boundaries. Snippet: ${snippet}"
  done || true
fi

# --- SEC-021: likely secret logging ---
if [ -d .github/workflows ]; then
  grep -rnE 'echo[[:space:]]+.*(\$|\{\{).*(TOKEN|SECRET|PASSWORD|API_KEY)' .github/workflows 2>/dev/null | while IFS= read -r line; do
    file=$(echo "$line" | cut -d: -f1)
    line_num=$(echo "$line" | cut -d: -f2)
    snippet=$(echo "$line" | cut -d: -f3- | head -c 200 | tr '|' ' ')
    emit "$file" "$line_num" "SEC-021" "high" "Possible secret echoed to logs. Snippet: ${snippet}"
  done || true
fi

# --- SEC-030: action uses not pinned to full commit SHA (heuristic) ---
if [ -d .github/workflows ]; then
  grep -rnE '^\s+uses:\s+' .github/workflows 2>/dev/null | while IFS= read -r line; do
    file=$(echo "$line" | cut -d: -f1)
    line_num=$(echo "$line" | cut -d: -f2)
    rest=$(echo "$line" | cut -d: -f3-)
    echo "$rest" | grep -q 'docker://' && continue
    ref=$(echo "$rest" | sed -n 's/.*@\([^[:space:]#]\+\).*/\1/p')
    [ -n "$ref" ] || continue
    if [[ "$ref" =~ ^\./ ]]; then
      continue
    fi
    if [[ "$ref" =~ ^[a-f0-9]{40}$ ]]; then
      continue
    fi
    emit "$file" "$line_num" "SEC-030" "medium" "Action ref is not a full 40-char SHA: @${ref}. Prefer pinning third-party actions to commit SHA."
  done || true
fi

# --- SEC-032: HTTP download in shell without obvious integrity check in same file ---
find . -path './.git' -prune -o -path './node_modules' -prune -o -path './vendor' -prune -o \
  -type f \( -name '*.sh' -o -name '*.bash' \) -print 2>/dev/null | while IFS= read -r f; do
  [ -f "$f" ] || continue
  if grep -qE '\b(curl|wget)\b' "$f" 2>/dev/null; then
    if ! grep -qE '(sha256sum|shasum|sha384sum|gpg|minisign|cosign)' "$f" 2>/dev/null; then
      line_num=$(grep -nE '\b(curl|wget)\b' "$f" | head -1 | cut -d: -f1)
      emit "$f" "${line_num:-1}" "SEC-032" "high" "Download via curl/wget without obvious checksum/signature verification in this script."
    fi
  fi
done

# --- SEC-040: overly broad permissions ---
if [ -d .github/workflows ]; then
  grep -rnE 'write-all|contents:\s*write' .github/workflows 2>/dev/null | while IFS= read -r line; do
    file=$(echo "$line" | cut -d: -f1)
    line_num=$(echo "$line" | cut -d: -f2)
    snippet=$(echo "$line" | cut -d: -f3- | head -c 200 | tr '|' ' ')
    emit "$file" "$line_num" "SEC-040" "medium" "Review permissions for least privilege. Snippet: ${snippet}"
  done || true
fi

# --- SEC-043: pull_request_target (high-risk trigger; review secret + checkout usage) ---
if [ -d .github/workflows ]; then
  grep -rn 'pull_request_target' .github/workflows 2>/dev/null | while IFS= read -r line; do
    file=$(echo "$line" | cut -d: -f1)
    line_num=$(echo "$line" | cut -d: -f2)
    emit "$file" "$line_num" "SEC-043" "medium" "pull_request_target present; verify against GitHub hardening guidance for fork PRs and secrets."
  done || true
fi

# --- SEC-033: npm audit (when Node lockfile and npm available) ---
if command -v npm >/dev/null 2>&1; then
  find . -path './.git' -prune -o -path './node_modules' -prune -o -path './vendor' -prune -o \
    -type f -name 'package-lock.json' -print 2>/dev/null | while IFS= read -r lockfile; do
      [ -f "$lockfile" ] || continue
      lockdir=$(dirname "$lockfile")
      audit_json=$(cd "$lockdir" && npm audit --json 2>/dev/null || true)
      if echo "$audit_json" | jq -e '(.metadata.vulnerabilities.total // 0) > 0' >/dev/null 2>&1; then
        total=$(echo "$audit_json" | jq -r '.metadata.vulnerabilities.total // 0')
        emit "$lockfile" "1" "SEC-033" "high" "npm audit reports ${total} vulnerability row(s); review advisories and update dependencies."
      fi
    done
fi

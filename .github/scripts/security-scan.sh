#!/usr/bin/env bash
# Security scan for oblt-aw detector.
# Runs shellcheck on shell scripts and grep for token exposure patterns.
# Output format: file|line|rule|severity|message
set -euo pipefail

REPO_ROOT="${1:-.}"
cd "$REPO_ROOT"

# Discover and scan shell scripts (exclude .git, node_modules, vendor)
find . -path './.git' -prune -o -path './node_modules' -prune -o -path './vendor' -prune -o \
  -type f \( -name '*.sh' -o -name '*.bash' \) -print 2>/dev/null | while IFS= read -r f; do
  [ -f "$f" ] || continue
  shellcheck -f json1 "$f" 2>/dev/null | jq -r --arg file "$f" '
    .comments[]? | "\($file)|\(.line)|SHELLCHECK|\(.level)|\(.message)"
  ' 2>/dev/null || true
done

# Pattern checks: ${{ secrets.* }} in workflow files (SEC-001, SEC-002)
if [ -d .github/workflows ]; then
  # shellcheck disable=SC2016
  grep -rn '\${{ secrets\.' .github/workflows/ 2>/dev/null | grep -vE '^\S+:[0-9]+:\s*[A-Z][A-Z0-9_]*:\s*\$' | while IFS= read -r line; do
    file=$(echo "$line" | cut -d: -f1)
    line_num=$(echo "$line" | cut -d: -f2)
    snippet=$(echo "$line" | cut -d: -f3- | head -c 200 | tr '|' ' ')
    echo "${file}|${line_num}|SEC-002|high|Potential token exposure in command context. Use env: to pass secrets. Snippet: ${snippet}"
  done || true
fi

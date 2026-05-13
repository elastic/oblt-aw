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
# Uses actionlint, zizmor, semgrep (when installed), shellcheck, npm audit, and
# minimal custom checks. Aligned with docs/workflows/security-scanning-ruleset.md.
# Output format: file|line|rule|severity|message
set -euo pipefail

REPO_ROOT="${1:-.}"
REPO_ROOT="$(cd "$REPO_ROOT" && pwd)"

if ! command -v jq >/dev/null 2>&1; then
  echo "security-scan.sh: jq is required" >&2
  exit 1
fi

emit() {
  echo "$1|$2|$3|$4|$5"
}

# Collect findings here, then dedupe by file|line (keep highest severity).
FINDINGS_TMP="${TMPDIR:-/tmp}/security-scan-$$.txt"
touch "$FINDINGS_TMP"
cleanup() { rm -f "$FINDINGS_TMP"; }
trap cleanup EXIT

# --- SEC-011: standalone shell scripts (shellcheck) ---
(
  cd "$REPO_ROOT" || exit 0
  find . -path './.git' -prune -o -path './node_modules' -prune -o -path './vendor' -prune -o \
    -type f \( -name '*.sh' -o -name '*.bash' \) -print 2>/dev/null
) | while IFS= read -r f; do
  [ -f "$REPO_ROOT/${f#./}" ] || continue
  shellcheck -f json1 "$REPO_ROOT/${f#./}" 2>/dev/null | jq -r --arg file "${f#./}" '
    .comments[]? |
    (if .level == "error" then "high"
     elif .level == "warning" then "medium"
     elif .level == "info" then "low"
     else "low" end) as $sev |
    "\($file)|\(.line // 1)|SEC-011|\($sev)|shellcheck [\(.level)]: \(.message | gsub("\\|"; " "))"
  ' 2>/dev/null || true
done >>"$FINDINGS_TMP" || true

# --- actionlint: workflow expressions, credentials, shellcheck on run: blocks ---
if [ -d "$REPO_ROOT/.github/workflows" ] && command -v actionlint >/dev/null 2>&1; then
  # shellcheck disable=SC2016
  (cd "$REPO_ROOT" && actionlint -format '{{json .}}' 2>/dev/null || true) | jq -r --arg root "$REPO_ROOT" '
    .[] |
    select(
      .kind == "credentials" or
      .kind == "shellcheck" or
      (.kind == "expression" and (
        (.message | test("untrusted|secret|password|credential|inject"; "i"))
      ))
    ) |
    .filepath as $fp |
    .line as $ln |
    .kind as $k |
    (if $k == "credentials" then "SEC-020"
     elif $k == "shellcheck" then "SEC-011"
     elif (.message | test("secret"; "i")) then "SEC-002"
     else "SEC-010" end) as $rule |
    (if $k == "credentials" then "high"
     elif $k == "shellcheck" then "medium"
     else "high" end) as $sev |
    "\($fp)|\($ln)|\($rule)|\($sev)|actionlint [\($k)]: \(.message | gsub("\\|"; " "))"
  ' >>"$FINDINGS_TMP" 2>/dev/null || true
fi

# --- zizmor: GitHub Actions security audits (offline; pin / permissions / injection / secrets, etc.) ---
if [ -d "$REPO_ROOT/.github/workflows" ] && command -v zizmor >/dev/null 2>&1; then
  zizmor --offline --format=json-v1 --collect=workflows "$REPO_ROOT" 2>/dev/null | jq -r --arg root "$REPO_ROOT" '
    def rel_path($p):
      if $p == null or $p == "" then empty
      elif ($p | startswith($root)) then
        ($p | .[($root | length):] | if startswith("/") then .[1:] else . end)
      elif ($p | startswith("./")) then ($p | .[2:])
      else $p end;

    def strip_root($p):
      if ($p | startswith($root)) then
        ($p | .[($root | length):] | if startswith("/") then .[1:] else . end)
      else $p end;

    def sec_for($id):
      {
        "template-injection": "SEC-010",
        "dangerous-triggers": "SEC-043",
        "excessive-permissions": "SEC-040",
        "undocumented-permissions": "SEC-040",
        "unpinned-uses": "SEC-030",
        "unpinned-images": "SEC-030",
        "stale-action-refs": "SEC-030",
        "ref-confusion": "SEC-030",
        "ref-version-mismatch": "SEC-030",
        "impostor-commit": "SEC-030",
        "secrets-outside-env": "SEC-002",
        "unredacted-secrets": "SEC-021",
        "hardcoded-container-credentials": "SEC-020",
        "overprovisioned-secrets": "SEC-022",
        "secrets-inherit": "SEC-022",
        "github-env": "SEC-010",
        "insecure-commands": "SEC-011",
        "cache-poisoning": "SEC-012",
        "known-vulnerable-actions": "SEC-031",
        "forbidden-uses": "SEC-031",
        "archived-uses": "SEC-031",
        "artipacked": "SEC-031",
        "anonymous-definition": "SEC-012",
        "bot-conditions": "SEC-012",
        "dependabot-execution": "SEC-035",
        "self-hosted-runner": "SEC-042",
        "misfeature": "SEC-012",
        "obfuscation": "SEC-012",
        "unsound-condition": "SEC-012",
        "unsound-contains": "SEC-012",
        "concurrency-limits": "SEC-012",
        "superfluous-actions": "SEC-012",
        "use-trusted-publishing": "SEC-012"
      }[$id] // "SEC-012";

    def sev_map:
      {
        "critical": "critical",
        "high": "high",
        "medium": "medium",
        "low": "low",
        "informational": "low"
      };

    .[] |
    . as $finding |
    (.locations | map(select(.symbolic.kind == "Primary")) | if length > 0 then . else [ .locations[0] ] end) |
    .[] |
    (try(.symbolic.key.Local.given_path) // "") as $gp |
    if $gp == "" then empty else
      ($gp | rel_path($root)) as $rel |
      (if ($rel | length) == 0 then $gp else $rel end) as $rel2 |
      (strip_root($rel2)) as $rel3 |
      (.concrete.location.start_point.row // 0) as $row0 |
      (($row0 + 1) | tostring) as $line |
      ($finding.ident) as $id |
      ($finding.determinations.severity // "Medium" | ascii_downcase) as $zs |
      (sev_map[$zs] // "medium") as $sev |
      (sec_for($id)) as $rule |
      (if $rule == "SEC-030" then "medium" else $sev end) as $sev2 |
      "\($rel3)|\($line)|\($rule)|\($sev2)|zizmor [\($id)]: \($finding.desc | gsub("\\|"; " ")) (\($finding.url))"
    end
  ' >>"$FINDINGS_TMP" 2>/dev/null || true
fi

# --- semgrep: community GitHub Actions rules (complements zizmor/actionlint) ---
if [ -d "$REPO_ROOT/.github/workflows" ] && command -v semgrep >/dev/null 2>&1; then
  (
    cd "$REPO_ROOT" &&
      semgrep scan --config p/github-actions --json -q .github/workflows 2>/dev/null || true
  ) | jq -r --arg root "$REPO_ROOT" '
    def rel_path($p):
      if $p == null or $p == "" then ""
      elif ($p | startswith($root)) then
        ($p | .[($root | length):] | if startswith("/") then .[1:] else . end)
      else $p end;

    .results[]? |
    (.path | rel_path($root)) as $p |
    (.start.line // 1 | tostring) as $ln |
    .check_id as $cid |
    (.extra.message // "" | gsub("\\|"; " ")) as $msg |
    (.extra.severity // "INFO") as $sv |
    (if ($sv == "ERROR" or $sv == "error") then "high"
     elif ($sv == "WARNING" or $sv == "warning") then "medium"
     else "low" end) as $sev |
    (if ($cid | test("injection|insecure|secret|credential"; "i")) then "SEC-010"
     else "SEC-012" end) as $rule |
    "\($p)|\($ln)|\($rule)|\($sev)|semgrep [\($cid)]: \($msg)"
  ' >>"$FINDINGS_TMP" 2>/dev/null || true
fi

# --- SEC-032: HTTP download in shell without obvious integrity check in same file ---
(
  cd "$REPO_ROOT" || exit 0
  find . -path './.git' -prune -o -path './node_modules' -prune -o -path './vendor' -prune -o \
    -type f \( -name '*.sh' -o -name '*.bash' \) -print 2>/dev/null
) | while IFS= read -r f; do
  fp="$REPO_ROOT/${f#./}"
  [ -f "$fp" ] || continue
  if grep -qE '\b(curl|wget)\b' "$fp" 2>/dev/null; then
    if ! grep -qE '(sha256sum|shasum|sha384sum|gpg|minisign|cosign)' "$fp" 2>/dev/null; then
      line_num=$(grep -nE '\b(curl|wget)\b' "$fp" | head -1 | cut -d: -f1)
      emit "${f#./}" "${line_num:-1}" "SEC-032" "high" "Download via curl/wget without obvious checksum/signature verification in this script." >>"$FINDINGS_TMP"
    fi
  fi
done || true

# --- SEC-033: npm audit (when Node lockfile and npm available) ---
if command -v npm >/dev/null 2>&1; then
  (
    cd "$REPO_ROOT" || exit 0
    find . -path './.git' -prune -o -path './node_modules' -prune -o -path './vendor' -prune -o \
      -type f -name 'package-lock.json' -print 2>/dev/null
  ) | while IFS= read -r f; do
      lockfile="$REPO_ROOT/${f#./}"
      [ -f "$lockfile" ] || continue
      lockdir=$(dirname "$lockfile")
      audit_json=$(cd "$lockdir" && npm audit --json 2>/dev/null || echo '{}')
      if echo "$audit_json" | jq -e '(.metadata.vulnerabilities.total // 0) > 0' >/dev/null 2>&1; then
        total=$(echo "$audit_json" | jq -r '.metadata.vulnerabilities.total // 0')
        emit "${f#./}" "1" "SEC-033" "high" "npm audit reports ${total} vulnerability row(s); review advisories and update dependencies." \
          >>"$FINDINGS_TMP"
      fi
    done
fi

# --- Dedupe: same file + line → keep highest severity; merge messages with " | " on tie ---
awk -F'|' '
function rank(s) {
  if (s == "critical") return 5
  if (s == "high") return 4
  if (s == "medium") return 3
  if (s == "low") return 2
  return 1
}
{
  if (NF < 5) next
  file = $1
  line = $2
  rule = $3
  sev = $4
  msg = $5
  for (i = 6; i <= NF; i++) msg = msg "|" $i
  key = file SUBSEP line
  r = rank(sev)
  if (!(key in bestr) || r > bestr[key]) {
    bestr[key] = r
    outrule[key] = rule
    outsev[key] = sev
    outmsg[key] = msg
  } else if (r == bestr[key] && index(outmsg[key], msg) == 0) {
    outmsg[key] = outmsg[key] " | " msg
  }
}
END {
  for (k in outmsg) {
    split(k, a, SUBSEP)
    print a[1] "|" a[2] "|" outrule[k] "|" outsev[k] "|" outmsg[k]
  }
}
' "$FINDINGS_TMP" | sort -t'|' -k1,1 -k2,2n

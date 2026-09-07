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

# Build a truncated Markdown snapshot of an issue for issue-fixer prompts.
# Prefer triage-style comments so the agent can start without a blind GitHub fetch.
#
# Usage:
#   build-fixer-issue-snapshot.sh <issue_number>
#
# Environment:
#   GITHUB_REPOSITORY (required unless SNAPSHOT_FIXTURE is set)
#   GH_TOKEN (required unless SNAPSHOT_FIXTURE is set)
#   SNAPSHOT_FIXTURE (optional path to JSON with .issue and .comments arrays)
#   MAX_TOTAL_CHARS (optional, default 12000)
#   MAX_BODY_CHARS (optional, default 2000)
#   MAX_COMMENT_CHARS (optional, default 4000)
#   MAX_COMMENTS (optional, default 5)
#
# Writes the snapshot to stdout. When GITHUB_OUTPUT is set, also writes a
# multiline `snapshot` output suitable for workflow job outputs.
set -euo pipefail

log() {
  printf '%s\n' "$*" >&2
}

die() {
  log "ERROR: $*"
  exit 1
}

truncate_text() {
  local text="$1"
  local max="$2"
  local len="${#text}"
  if (( len <= max )); then
    printf '%s' "$text"
    return
  fi
  printf '%s\n\n… truncated (%s chars total; showing first %s) …' "${text:0:max}" "$len" "$max"
}

ISSUE_NUMBER="${1:-}"
[[ -n "$ISSUE_NUMBER" ]] || die "usage: $0 <issue_number>"

MAX_TOTAL_CHARS="${MAX_TOTAL_CHARS:-12000}"
MAX_BODY_CHARS="${MAX_BODY_CHARS:-2000}"
MAX_COMMENT_CHARS="${MAX_COMMENT_CHARS:-4000}"
MAX_COMMENTS="${MAX_COMMENTS:-5}"

if [[ -n "${SNAPSHOT_FIXTURE:-}" ]]; then
  [[ -f "$SNAPSHOT_FIXTURE" ]] || die "SNAPSHOT_FIXTURE not found: $SNAPSHOT_FIXTURE"
  payload="$(cat "$SNAPSHOT_FIXTURE")"
else
  [[ -n "${GITHUB_REPOSITORY:-}" ]] || die "GITHUB_REPOSITORY is required"
  [[ -n "${GH_TOKEN:-}" ]] || die "GH_TOKEN is required"
  issue_json="$(gh api "repos/${GITHUB_REPOSITORY}/issues/${ISSUE_NUMBER}")"
  comments_json="$(gh api "repos/${GITHUB_REPOSITORY}/issues/${ISSUE_NUMBER}/comments?per_page=100")"
  payload="$(jq -n --argjson issue "$issue_json" --argjson comments "$comments_json" \
    '{issue: $issue, comments: $comments}')"
fi

title="$(jq -r '.issue.title // ""' <<<"$payload")"
labels="$(jq -r '[.issue.labels[]?.name] // [] | join(", ")' <<<"$payload")"
body="$(jq -r '.issue.body // ""' <<<"$payload")"
body_trunc="$(truncate_text "$body" "$MAX_BODY_CHARS")"

# Prefer triage-like comments, then fill with newest remaining (jq-only; no mapfile).
selected_csv="$(
  jq -r \
    --argjson max_comments "$MAX_COMMENTS" \
    '
    def triage:
      (.body // "") as $b
      | ($b | test("Detailed Action Plan|Action Plan|Recommendation|tl;dr|oblt-aw/triage/"));
    (.comments // []) as $c
    | ($c | length) as $n
    | [range(0; $n)] | reverse as $newest
    | reduce $newest[] as $i (
        {triage: [], other: []};
        if ($c[$i] | triage) then .triage += [$i] else .other += [$i] end
      )
    | ((.triage + .other) | .[0:$max_comments] | map(tostring) | join(","))
    ' <<<"$payload"
)"

snapshot_file="${TMPDIR:-/tmp}/fixer-issue-snapshot.$$.md"
{
  echo "## Issue snapshot (preloaded for this fixer run)"
  echo
  echo "- **Number:** #${ISSUE_NUMBER}"
  echo "- **Title:** ${title}"
  echo "- **Labels:** ${labels:-"(none)"}"
  echo
  echo "### Issue body (may be truncated)"
  echo
  echo "$body_trunc"
  echo
  echo "### Selected comments (newest / triage-like preferred; may be truncated)"
  echo
  if [[ -z "$selected_csv" ]]; then
    echo "_No comments available in this snapshot._"
  else
    old_ifs="$IFS"
    IFS=','
    # shellcheck disable=SC2086
    set -- $selected_csv
    IFS="$old_ifs"
    for idx in "$@"; do
      [[ -n "$idx" ]] || continue
      author="$(jq -r --argjson i "$idx" '.comments[$i].user.login // "unknown"' <<<"$payload")"
      created="$(jq -r --argjson i "$idx" '.comments[$i].created_at // ""' <<<"$payload")"
      cbody="$(jq -r --argjson i "$idx" '.comments[$i].body // ""' <<<"$payload")"
      cbody_trunc="$(truncate_text "$cbody" "$MAX_COMMENT_CHARS")"
      echo "#### Comment by @${author} (${created})"
      echo
      echo "$cbody_trunc"
      echo
    done
  fi
  echo
  echo "Use this snapshot as the starting point. If more detail is required, read via GitHub MCP / \`github\` CLI (not shell \`gh\`)."
} >"$snapshot_file"

snapshot="$(cat "$snapshot_file")"
rm -f "$snapshot_file"
snapshot="$(truncate_text "$snapshot" "$MAX_TOTAL_CHARS")"

printf '%s\n' "$snapshot"

if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  delimiter="SNAPSHOT_EOF_$$"
  {
    echo "snapshot<<${delimiter}"
    printf '%s\n' "$snapshot"
    echo "${delimiter}"
  } >>"$GITHUB_OUTPUT"
fi

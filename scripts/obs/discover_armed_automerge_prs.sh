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

# List open PRs with a bot-authored armed marker for the current head SHA.
# Label filtering happens in the merge matrix (consumer trigger-label policy).
# Writes GitHub Actions outputs: candidates (JSON array), has-candidates (true|false).
set -euo pipefail

REPO="${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
OUT="${GITHUB_OUTPUT:?GITHUB_OUTPUT is required}"
# Cap matrix size (GitHub Actions matrix max is 256). Extra armed PRs wait for
# the next frequent-schedule tick.
MAX_CANDIDATES="${AUTOMERGE_DISCOVER_MAX_CANDIDATES:-100}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=automerge_armed_lib.sh
# shellcheck disable=SC1091 # sourced via SCRIPT_DIR; file lives next to this script
source "${SCRIPT_DIR}/automerge_armed_lib.sh"

candidates='[]'
scanned=0
truncated=0
while IFS=$'\t' read -r pr_number head_sha; do
  [[ -n "${pr_number}" && -n "${head_sha}" ]] || continue
  scanned=$((scanned + 1))
  comments_json="$(automerge_list_issue_comments "${REPO}" "${pr_number}")" || {
    echo "Failed to list comments for PR #${pr_number}; aborting discover." >&2
    exit 1
  }
  if automerge_comments_armed_for_sha "${comments_json}" "${head_sha}"; then
    candidate_count="$(jq 'length' <<<"${candidates}")"
    if [[ "${candidate_count}" -ge "${MAX_CANDIDATES}" ]]; then
      truncated=$((truncated + 1))
      echo "PR #${pr_number}: armed but held for a later tick (matrix cap ${MAX_CANDIDATES})"
      continue
    fi
    candidates="$(jq -c --arg n "${pr_number}" --arg s "${head_sha}" \
      '. + [{pr_number: $n, head_sha: $s}]' <<<"${candidates}")"
    echo "PR #${pr_number}: deferred candidate (head ${head_sha})"
  else
    echo "PR #${pr_number}: deferred skip (not armed for head ${head_sha})"
  fi
done < <(
  # Paginate every open PR — do not stop at the first page (label filter removed).
  gh api --paginate "repos/${REPO}/pulls?state=open&per_page=100" \
    --jq '.[] | select(.head.sha != null and .head.sha != "") | "\(.number)\t\(.head.sha)"'
)

{
  echo "candidates<<EOF"
  echo "${candidates}"
  echo "EOF"
  if [[ "${candidates}" == '[]' ]]; then
    echo "has-candidates=false"
  else
    echo "has-candidates=true"
  fi
} >>"${OUT}"

echo "Automerge deferred: scanned ${scanned} open PR(s); $(jq 'length' <<<"${candidates}") armed candidate(s) for schedule"
if [[ "${truncated}" -gt 0 ]]; then
  echo "Automerge deferred: ${truncated} additional armed PR(s) capped for later schedule ticks (max ${MAX_CANDIDATES})." >&2
fi

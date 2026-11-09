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

# List open PRs with a bot-authored armed marker for the current head SHA and at
# least one effective consumer trigger label (AUTOMERGE_TRIGGER_LABELS_JSON).
# Writes GitHub Actions outputs: candidates (JSON array), has-candidates (true|false).
set -euo pipefail

REPO="${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
OUT="${GITHUB_OUTPUT:?GITHUB_OUTPUT is required}"
# Cap matrix size (GitHub Actions matrix max is 256). Extra eligible PRs rotate
# across frequent-schedule ticks.
MAX_CANDIDATES="${AUTOMERGE_DISCOVER_MAX_CANDIDATES:-100}"
RUN_NUMBER="${GITHUB_RUN_NUMBER:-0}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=automerge_armed_lib.sh
# shellcheck disable=SC1091 # sourced via SCRIPT_DIR; file lives next to this script
source "${SCRIPT_DIR}/automerge_armed_lib.sh"

eligible='[]'
scanned=0
opted_out=0
while IFS=$'\t' read -r pr_number head_sha; do
  [[ -n "${pr_number}" && -n "${head_sha}" ]] || continue
  scanned=$((scanned + 1))
  comments_json="$(automerge_list_issue_comments "${REPO}" "${pr_number}")" || {
    echo "Failed to list comments for PR #${pr_number}; aborting discover." >&2
    exit 1
  }
  if ! automerge_comments_armed_for_sha "${comments_json}" "${head_sha}"; then
    echo "PR #${pr_number}: deferred skip (not armed for head ${head_sha})"
    continue
  fi

  # Drop opted-out / label-stripped PRs before the matrix cap so they cannot
  # monopolize every schedule batch.
  label_rc=0
  automerge_pr_has_merge_ready_label "${REPO}" "${pr_number}" || label_rc=$?
  if [[ "${label_rc}" -eq 2 ]]; then
    opted_out=$((opted_out + 1))
    echo "PR #${pr_number}: deferred skip (armed but missing trigger label)"
    continue
  fi
  if [[ "${label_rc}" -ne 0 ]]; then
    echo "PR #${pr_number}: could not verify trigger labels; aborting discover." >&2
    exit 1
  fi

  eligible="$(jq -c --arg n "${pr_number}" --arg s "${head_sha}" \
    '. + [{pr_number: ($n | tonumber), head_sha: $s}]' <<<"${eligible}")"
  echo "PR #${pr_number}: eligible armed candidate (head ${head_sha})"
done < <(
  # Paginate every open PR — do not stop at the first page.
  gh api --paginate "repos/${REPO}/pulls?state=open&per_page=100" \
    --jq '.[] | select(.head.sha != null and .head.sha != "") | "\(.number)\t\(.head.sha)"'
)

# Stable order, then rotate the window across ticks so a stuck prefix cannot
# permanently starve later PRs. Matrix expects string pr_number.
eligible="$(jq -c 'sort_by(.pr_number)' <<<"${eligible}")"
eligible_count="$(jq 'length' <<<"${eligible}")"
candidates='[]'
if [[ "${eligible_count}" -gt 0 ]]; then
  start=0
  if [[ "${eligible_count}" -gt "${MAX_CANDIDATES}" ]]; then
    start=$(( (RUN_NUMBER * MAX_CANDIDATES) % eligible_count ))
  fi
  candidates="$(jq -c --argjson start "${start}" --argjson max "${MAX_CANDIDATES}" '
    . as $all
    | ($all[$start:] + $all[:$start])[:$max]
    | map({pr_number: (.pr_number | tostring), head_sha})
  ' <<<"${eligible}")"
fi

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

candidate_count="$(jq 'length' <<<"${candidates}")"
echo "Automerge deferred: scanned ${scanned} open PR(s); ${opted_out} armed without trigger label; ${eligible_count} eligible; ${candidate_count} in this tick (max ${MAX_CANDIDATES})"
if [[ "${eligible_count}" -gt "${MAX_CANDIDATES}" ]]; then
  echo "Automerge deferred: ${eligible_count} eligible armed PR(s); rotating batch of ${MAX_CANDIDATES} this tick (run ${RUN_NUMBER})." >&2
fi

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

# List open merge-ready PRs with a bot-authored armed marker for the current head SHA.
# Writes GitHub Actions outputs: candidates (JSON array), has-candidates (true|false).
set -euo pipefail

REPO="${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
LABEL='oblt-aw/ai/merge-ready'
OUT="${GITHUB_OUTPUT:?GITHUB_OUTPUT is required}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=automerge_armed_lib.sh
# shellcheck disable=SC1091 # sourced via SCRIPT_DIR; file lives next to this script
source "${SCRIPT_DIR}/automerge_armed_lib.sh"

candidates='[]'
while IFS=$'\t' read -r pr_number head_sha; do
  [[ -n "${pr_number}" && -n "${head_sha}" ]] || continue
  comments_json="$(automerge_list_issue_comments "${REPO}" "${pr_number}")" || {
    echo "Failed to list comments for PR #${pr_number}; aborting discover." >&2
    exit 1
  }
  if automerge_comments_armed_for_sha "${comments_json}" "${head_sha}"; then
    candidates="$(jq -c --arg n "${pr_number}" --arg s "${head_sha}" \
      '. + [{pr_number: $n, head_sha: $s}]' <<<"${candidates}")"
    echo "PR #${pr_number}: deferred candidate (head ${head_sha})"
  else
    echo "PR #${pr_number}: deferred skip (not armed for head ${head_sha})"
  fi
done < <(
  gh pr list --repo "${REPO}" --state open --label "${LABEL}" --limit 100 \
    --json number,headRefOid \
    --jq '.[] | select(.headRefOid != null and .headRefOid != "") | "\(.number)\t\(.headRefOid)"'
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

echo "Automerge deferred: $(jq 'length' <<<"${candidates}") armed merge-ready PR(s) for schedule"

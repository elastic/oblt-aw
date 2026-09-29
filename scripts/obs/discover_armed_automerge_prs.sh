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

# List open merge-ready PRs that carry the automerge armed comment marker.
# Writes GitHub Actions outputs: candidates (JSON array), has-candidates (true|false).
set -euo pipefail

REPO="${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
MARKER='<!-- obs-aw-automerge:armed -->'
LABEL='oblt-aw/ai/merge-ready'
OUT="${GITHUB_OUTPUT:?GITHUB_OUTPUT is required}"

candidates='[]'
while IFS=$'\t' read -r pr_number head_sha; do
  [[ -n "${pr_number}" && -n "${head_sha}" ]] || continue
  if comment_id="$(gh api "repos/${REPO}/issues/${pr_number}/comments" --paginate \
    | jq --arg m "${MARKER}" -r '.[] | select((.body // "") | contains($m)) | .id' \
    | head -n 1)" && [[ -n "${comment_id}" ]]; then
    candidates="$(jq -c --arg n "${pr_number}" --arg s "${head_sha}" \
      '. + [{pr_number: $n, head_sha: $s}]' <<<"${candidates}")"
    echo "PR #${pr_number}: deferred candidate (head ${head_sha})"
  else
    echo "PR #${pr_number}: deferred skip (not armed)"
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

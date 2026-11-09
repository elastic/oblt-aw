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
# least one effective trigger label from that PR's base-SHA consumer policy.
# Writes GitHub Actions outputs: candidates (JSON array), has-candidates (true|false).
#
# Required env:
#   GITHUB_REPOSITORY, GITHUB_OUTPUT, GH_TOKEN
# Optional:
#   OBLT_AW_ROOT — checkout of elastic/oblt-aw with resolve_automerge_policy_cli.py.
#     When unset or the resolver is missing (legacy @v0 sparse fetch of this script
#     alone), discover falls back to merge-ready-only label filtering.
#   ORG_KEY — consuming org key for apm.yml resolve (default obs)
#   AUTOMERGE_DISCOVER_MAX_CANDIDATES (default 100)
#   GITHUB_RUN_NUMBER — rotates the eligible batch across ticks
#   POLICY_CACHE_DIR — directory for per-base-SHA policy cache
set -euo pipefail

REPO="${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
OUT="${GITHUB_OUTPUT:?GITHUB_OUTPUT is required}"
ORG_KEY="${ORG_KEY:-obs}"
MAX_CANDIDATES="${AUTOMERGE_DISCOVER_MAX_CANDIDATES:-100}"
RUN_NUMBER="${GITHUB_RUN_NUMBER:-0}"
POLICY_CACHE_DIR="${POLICY_CACHE_DIR:-${RUNNER_TEMP:-/tmp}/automerge-policy-by-base}"
OBLT_AW_ROOT="${OBLT_AW_ROOT:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=automerge_armed_lib.sh
# shellcheck disable=SC1091 # sourced via SCRIPT_DIR; file lives next to this script
source "${SCRIPT_DIR}/automerge_armed_lib.sh"

LEGACY_MERGE_READY_ONLY=false
if [[ -z "${OBLT_AW_ROOT}" || ! -f "${OBLT_AW_ROOT}/scripts/resolve_automerge_policy_cli.py" ]]; then
  LEGACY_MERGE_READY_ONLY=true
  echo "Discover: OBLT_AW_ROOT/resolver unavailable; using merge-ready-only legacy path." >&2
else
  mkdir -p "${POLICY_CACHE_DIR}"
fi

# Resolve trigger-labels JSON for a trusted PR base SHA (cached on disk).
# Prints a JSON string array to stdout.
automerge_discover_triggers_for_base_sha() {
  local base_sha="${1:?base sha required}"
  local cache_file="${POLICY_CACHE_DIR}/${base_sha}.triggers.json"
  local work_dir
  local name
  local encoded
  local policy_json
  local triggers
  local gh_out

  if [[ -f "${cache_file}" ]]; then
    cat "${cache_file}"
    return 0
  fi

  work_dir="$(mktemp -d "${POLICY_CACHE_DIR}/work.XXXXXX")"
  # Fetch apm.yml / apm.yaml at the trusted base SHA (never PR head).
  for name in apm.yml apm.yaml; do
    set +e
    gh_out="$(gh api "repos/${REPO}/contents/${name}?ref=${base_sha}" 2>/dev/null)"
    set -e
    if [[ -n "${gh_out}" ]]; then
      encoded="$(printf '%s' "${gh_out}" | jq -r '.content // empty')"
      if [[ -n "${encoded}" && "${encoded}" != "null" ]]; then
        printf '%s' "${encoded}" | tr -d '\n' | base64 --decode >"${work_dir}/${name}"
        break
      fi
    fi
  done

  policy_json="$(
    REPO_ROOT="${work_dir}" \
      ORG_KEY="${ORG_KEY}" \
      PYTHONPATH="${OBLT_AW_ROOT}/scripts${PYTHONPATH:+:${PYTHONPATH}}" \
      GITHUB_OUTPUT="${work_dir}/github_output" \
      python3 "${OBLT_AW_ROOT}/scripts/resolve_automerge_policy_cli.py"
  )"
  triggers="$(printf '%s' "${policy_json}" | jq -c '."trigger-labels" // ["oblt-aw/ai/merge-ready"]')"
  printf '%s\n' "${triggers}" >"${cache_file}"
  rm -rf "${work_dir}"
  printf '%s\n' "${triggers}"
}

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

  if [[ "${LEGACY_MERGE_READY_ONLY}" == "true" ]]; then
    # Self-contained path for @v0 callers that only sparse-fetch this script.
    unset AUTOMERGE_TRIGGER_LABELS_JSON || true
    base_sha="legacy"
  else
    base_sha="$(gh api "repos/${REPO}/pulls/${pr_number}" --jq '.base.sha')" || {
      echo "Failed to resolve base.sha for ${REPO}#${pr_number}; aborting discover." >&2
      exit 1
    }
    if [[ -z "${base_sha}" || "${base_sha}" == "null" ]]; then
      echo "Empty base.sha for ${REPO}#${pr_number}; aborting discover." >&2
      exit 1
    fi
    AUTOMERGE_TRIGGER_LABELS_JSON="$(automerge_discover_triggers_for_base_sha "${base_sha}")"
    export AUTOMERGE_TRIGGER_LABELS_JSON
  fi

  # Drop opted-out / label-stripped PRs before the matrix cap so they cannot
  # monopolize every schedule batch.
  label_rc=0
  automerge_pr_has_merge_ready_label "${REPO}" "${pr_number}" || label_rc=$?
  if [[ "${label_rc}" -eq 2 ]]; then
    opted_out=$((opted_out + 1))
    echo "PR #${pr_number}: deferred skip (armed but missing trigger label for base ${base_sha:0:7})"
    continue
  fi
  if [[ "${label_rc}" -ne 0 ]]; then
    echo "PR #${pr_number}: could not verify trigger labels; aborting discover." >&2
    exit 1
  fi

  eligible="$(jq -c --arg n "${pr_number}" --arg s "${head_sha}" \
    '. + [{pr_number: ($n | tonumber), head_sha: $s}]' <<<"${eligible}")"
  echo "PR #${pr_number}: eligible armed candidate (head ${head_sha}; base ${base_sha:0:7})"
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

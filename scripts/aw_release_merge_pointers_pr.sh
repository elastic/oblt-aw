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

# Approve (APPROVE_TOKEN) and squash-merge (GH_TOKEN) a release-pointers PR.
# Org rules require a PR into main; GITHUB_TOKEN cannot push directly.
#
# Required env:
#   APPROVE_TOKEN       Token for a different actor than the PR author (usually GITHUB_TOKEN)
#   GH_TOKEN            Vault app token (merge + PR reads)
#   GITHUB_REPOSITORY   owner/repo
#   PR_NUMBER           Pull request number
# Optional env:
#   MERGE_POLL_SECONDS     default 5
#   MERGE_TIMEOUT_SECONDS  default 300

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=obs/automerge_armed_lib.sh
# shellcheck disable=SC1091 # sourced via SCRIPT_DIR; file lives under scripts/obs/
source "${SCRIPT_DIR}/obs/automerge_armed_lib.sh"

aw_release_merge_error_is_retryable() {
  local msg="${1:-}"
  if automerge_merge_error_is_pending_checks "${msg}"; then
    return 0
  fi
  # Copilot / review / base-branch freshness often clears on a short poll.
  printf '%s' "${msg}" | grep -qiE \
    'review|approv|copilot|not mergeable|head branch|base branch was modified|required status'
}

aw_release_approve_pr() {
  local repo="${1:?}"
  local pr_number="${2:?}"
  local approve_token="${3:?}"
  local out
  if out="$(
    GH_TOKEN="${approve_token}" gh pr review "${pr_number}" \
      --repo "${repo}" \
      --approve 2>&1
  )"; then
    echo "Approved PR #${pr_number}"
    return 0
  fi
  if printf '%s' "${out}" | grep -qiE 'already reviewed|already approved'; then
    echo "PR #${pr_number} already approved"
    return 0
  fi
  echo "Approve failed for PR #${pr_number}: ${out}" >&2
  return 1
}

aw_release_squash_merge_pr() {
  local repo="${1:?}"
  local pr_number="${2:?}"
  local head_sha="${3:?}"
  local commit_title="${4:?}"
  local merge_out
  if merge_out="$(
    gh api --method PUT "repos/${repo}/pulls/${pr_number}/merge" \
      -f merge_method=squash \
      -f sha="${head_sha}" \
      -f commit_title="${commit_title}" 2>&1
  )"; then
    echo "Merged PR #${pr_number} (squash) at ${head_sha:0:12}"
    return 0
  fi
  echo "${merge_out}"
  return 1
}

aw_release_wait_and_merge_pr() {
  local repo="${1:?}"
  local pr_number="${2:?}"
  local approve_token="${3:?}"
  local timeout_seconds="${4:-300}"
  local poll_seconds="${5:-5}"
  local deadline commit_title head_sha merge_out pr_state

  aw_release_approve_pr "${repo}" "${pr_number}" "${approve_token}"

  commit_title="$(
    gh pr view "${pr_number}" --repo "${repo}" --json title --jq .title
  )"
  deadline=$((SECONDS + timeout_seconds))

  while ((SECONDS < deadline)); do
    pr_state="$(
      gh pr view "${pr_number}" --repo "${repo}" --json state,mergedAt \
        --jq '{state,mergedAt}'
    )"
    if [[ "$(printf '%s' "${pr_state}" | jq -r .state)" == "MERGED" ]] ||
      [[ "$(printf '%s' "${pr_state}" | jq -r .mergedAt)" != "null" ]]; then
      echo "PR #${pr_number} already merged"
      return 0
    fi

    head_sha="$(
      gh pr view "${pr_number}" --repo "${repo}" --json headRefOid --jq .headRefOid
    )"
    if [[ ! "${head_sha}" =~ ^[0-9a-f]{40}$ ]]; then
      echo "Could not resolve head SHA for PR #${pr_number}" >&2
      return 1
    fi

    if merge_out="$(
      aw_release_squash_merge_pr "${repo}" "${pr_number}" "${head_sha}" "${commit_title}" 2>&1
    )"; then
      printf '%s\n' "${merge_out}"
      return 0
    fi

    if automerge_merge_error_is_already_merged_message "${merge_out}"; then
      echo "PR #${pr_number} already merged"
      return 0
    fi

    if aw_release_merge_error_is_retryable "${merge_out}"; then
      echo "Merge not ready yet; retrying in ${poll_seconds}s: ${merge_out}"
      sleep "${poll_seconds}"
      continue
    fi

    echo "Merge failed for PR #${pr_number}: ${merge_out}" >&2
    return 1
  done

  echo "Timed out after ${timeout_seconds}s waiting to merge PR #${pr_number}" >&2
  return 1
}

# When sourced (unit tests), skip main.
if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
  return 0
fi

: "${APPROVE_TOKEN:?APPROVE_TOKEN is required}"
: "${GH_TOKEN:?GH_TOKEN is required}"
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
: "${PR_NUMBER:?PR_NUMBER is required}"

aw_release_wait_and_merge_pr \
  "${GITHUB_REPOSITORY}" \
  "${PR_NUMBER}" \
  "${APPROVE_TOKEN}" \
  "${MERGE_TIMEOUT_SECONDS:-300}" \
  "${MERGE_POLL_SECONDS:-5}"

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

# Shared helpers for automerge arm → deferred merge (marker + REST error class).
# Source this file; do not execute it directly.

AUTOMERGE_ARMED_BOT='github-actions[bot]'
AUTOMERGE_MERGE_READY_LABEL='oblt-aw/ai/merge-ready'
# HTML comment marker always includes the approved head SHA, e.g.
# <!-- obs-aw-automerge:armed sha=0123…abcdef -->

automerge_armed_marker_line() {
  local sha="${1:?head sha required}"
  if [[ ! "${sha}" =~ ^[0-9a-f]{40}$ ]]; then
    echo "automerge_armed_marker_line: expected 40-hex sha, got: ${sha}" >&2
    return 1
  fi
  printf '<!-- obs-aw-automerge:armed sha=%s -->' "${sha}"
}

# True when REST merge failed because required checks are still pending (retry later).
automerge_merge_error_is_pending_checks() {
  local msg="${1:-}"
  printf '%s' "${msg}" | grep -qiE \
    'required status check|[[:space:]]pending[[:space:]]|awaiting status|status checks? (are |have )?not|Must be green before merging'
}

# True when REST merge reported the PR was already merged (not merely closed).
automerge_merge_error_is_already_merged_message() {
  local msg="${1:-}"
  printf '%s' "${msg}" | grep -qiE 'already been merged'
}

# Live merge-ready label check.
# Exit 0 — label present; 2 — confirmed absent; 1 — API/parse error (not an opt-out).
automerge_pr_has_merge_ready_label() {
  local repo="${1:?repo required}"
  local pr_number="${2:?pr number required}"
  local labels_json
  local present
  labels_json="$(gh api "repos/${repo}/pulls/${pr_number}" --jq '[.labels[].name]')" || {
    echo "Failed to list labels for ${repo}#${pr_number}." >&2
    return 1
  }
  present="$(printf '%s' "${labels_json}" | jq -r --arg label "${AUTOMERGE_MERGE_READY_LABEL}" \
    'if type != "array" then error("expected label name array")
     elif index($label) != null then "true"
     else "false"
     end')" || {
    echo "Failed to parse labels for ${repo}#${pr_number}." >&2
    return 1
  }
  if [[ "${present}" == "true" ]]; then
    return 0
  fi
  return 2
}

# Squash-merge via REST bound to expected_sha (fail closed if live head differs).
# Prints MERGE_RESULT=merged|not_ready|merge_failed|skipped on stdout for workflow wiring.
# Exit 0 when the result is classified (including merge_failed / not_ready / skipped);
# exit 1 on head drift, label lookup errors, approval verify failures, or non-open non-MERGED.
# Requires automerge_require_pr_head_sha and automerge_assert_pr_has_approved_review
# from assert_automerge_approved_review.sh.
automerge_squash_merge_at_sha() {
  local repo="${1:?repo required}"
  local pr_number="${2:?pr number required}"
  local expected_sha="${3:?expected sha required}"
  local author_login="${4:?author login required}"
  local merge_out
  local pr_state
  local label_rc
  local assert_out
  local assert_rc

  if ! automerge_require_pr_head_sha "${repo}" "${pr_number}" "${expected_sha}"; then
    echo "MERGE_RESULT=merge_failed"
    return 1
  fi

  # Re-check live opt-in: maintainers may remove merge-ready after verify/approve.
  label_rc=0
  automerge_pr_has_merge_ready_label "${repo}" "${pr_number}" || label_rc=$?
  if [[ "${label_rc}" -eq 2 ]]; then
    echo "MERGE_RESULT=skipped"
    echo "Missing label ${AUTOMERGE_MERGE_READY_LABEL} on ${repo}#${pr_number}; skipping merge." >&2
    return 0
  fi
  if [[ "${label_rc}" -ne 0 ]]; then
    echo "MERGE_RESULT=merge_failed"
    echo "Could not verify ${AUTOMERGE_MERGE_READY_LABEL} on ${repo}#${pr_number}; failing closed." >&2
    return 1
  fi

  # Revalidate approval: dismissals between assert-approved-review and merge must fail closed.
  set +e
  assert_out="$(automerge_assert_pr_has_approved_review \
    "${repo}" "${pr_number}" "${author_login}" "${expected_sha}" 2>&1)"
  assert_rc=$?
  set -e
  printf '%s\n' "${assert_out}"
  if [[ "${assert_rc}" -eq 2 ]]; then
    echo "MERGE_RESULT=merge_failed"
    echo "Approval no longer present for head ${expected_sha} on ${repo}#${pr_number}; failing closed." >&2
    return 1
  fi
  if [[ "${assert_rc}" -ne 0 ]]; then
    echo "MERGE_RESULT=merge_failed"
    echo "Could not revalidate APPROVED review for ${repo}#${pr_number}; failing closed." >&2
    return 1
  fi

  if merge_out="$(gh api --method PUT "repos/${repo}/pulls/${pr_number}/merge" \
    -f merge_method=squash \
    -f sha="${expected_sha}" 2>&1)"; then
    echo "MERGE_RESULT=merged"
    echo "Merged via REST API at ${expected_sha}."
    return 0
  fi

  echo "REST merge error: ${merge_out}" >&2
  if automerge_merge_error_is_already_merged_message "${merge_out}"; then
    echo "MERGE_RESULT=merged"
    return 0
  fi
  if printf '%s' "${merge_out}" | grep -qiE 'pull request is not open'; then
    pr_state="$(gh pr view "${pr_number}" --repo "${repo}" --json state -q .state)"
    if [[ "${pr_state}" == "MERGED" ]]; then
      echo "MERGE_RESULT=merged"
      return 0
    fi
    echo "MERGE_RESULT=merge_failed"
    echo "PR not open and not MERGED (state=${pr_state}); failing." >&2
    return 1
  fi
  if automerge_merge_error_is_pending_checks "${merge_out}"; then
    echo "MERGE_RESULT=not_ready"
    echo "REST merge blocked by pending checks."
    return 0
  fi
  echo "MERGE_RESULT=merge_failed"
  echo "REST merge failed with a non-retryable error." >&2
  return 0
}

# List issue comments as JSON (paginated). Fails closed on API errors.
automerge_list_issue_comments() {
  local repo="${1:?}"
  local pr_number="${2:?}"
  gh api "repos/${repo}/issues/${pr_number}/comments" --paginate
}

# True when comments_json contains a bot-authored marker for this exact head SHA.
automerge_comments_armed_for_sha() {
  local comments_json="${1:?}"
  local head_sha="${2:?}"
  local match
  match="$(printf '%s' "${comments_json}" | jq -r \
    --arg bot "${AUTOMERGE_ARMED_BOT}" \
    --arg sha "${head_sha}" \
    '[.[]
      | select(.user.login == $bot)
      | ((.body // "")
          | capture("<!-- obs-aw-automerge:armed sha=(?<s>[0-9a-f]{40}) -->")? // empty
        )
      | .s
      | select(. == $sha)
     ] | first // empty')"
  [[ -n "${match}" ]]
}

# Find the workflow-authored armed comment id for this exact head SHA. Empty if none.
# Never returns a marker for a different SHA (avoids stale concurrent arms clobbering the current head).
automerge_find_bot_armed_comment_id_from_json() {
  local comments_json="${1:?}"
  local head_sha="${2:?}"
  printf '%s' "${comments_json}" | jq -r \
    --arg bot "${AUTOMERGE_ARMED_BOT}" \
    --arg sha "${head_sha}" \
    '[.[]
      | select(.user.login == $bot)
      | select(
          ((.body // "")
            | capture("<!-- obs-aw-automerge:armed sha=(?<s>[0-9a-f]{40}) -->")? // empty
          ).s == $sha
        )
      | .id
     ] | first // empty'
}

# Upsert a bot-owned armed comment bound to head_sha. Sets armed=true on GITHUB_OUTPUT when set.
# Updates only a marker for this SHA; creates a new comment when none exists (leaves other SHAs alone).
# Optional 5th arg: shared-token-policy (non-empty => Vault-app bypass wording).
automerge_upsert_armed_comment() {
  local repo="${1:?}"
  local pr_number="${2:?}"
  local head_sha="${3:?}"
  local run_url="${4:-}"
  local token_policy="${5:-}"
  local marker
  marker="$(automerge_armed_marker_line "${head_sha}")"
  local retry_blurb
  if [[ -n "${token_policy}" ]]; then
    retry_blurb="This run stays successful. Deferred automerge on the frequent schedule (about every 15 minutes) will retry the squash-merge as the Vault app (CODEOWNERS bypass via classic \`pull_request_bypassers\`) once GitHub reports all required checks green."
  else
    retry_blurb="This run stays successful. Deferred automerge on the frequent schedule (about every 15 minutes) will retry the squash-merge with the workflow token. Configure a non-empty \`shared-token-policy\` when CODEOWNERS bypass via a Vault app is required."
  fi
  local body
  body="$(printf '%s\n\n%s\n\n%s\n\n%s' \
    "${marker}" \
    "Automerge did not merge yet because this pull request is **not ready** (required status checks are still pending)." \
    "${retry_blurb}" \
    "Armed by workflow run: ${run_url} (head \`${head_sha}\`)")"
  local comments_json
  comments_json="$(automerge_list_issue_comments "${repo}" "${pr_number}")" || return 1
  local comment_id
  comment_id="$(automerge_find_bot_armed_comment_id_from_json "${comments_json}" "${head_sha}")"
  if [[ -n "${comment_id}" ]]; then
    gh api --method PATCH "repos/${repo}/issues/comments/${comment_id}" -f body="${body}" >/dev/null
  else
    gh pr comment "${pr_number}" --repo "${repo}" --body "${body}"
  fi
  if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
    echo "armed=true" >>"${GITHUB_OUTPUT}"
  fi
}
